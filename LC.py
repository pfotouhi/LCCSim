import sys
from sys import argv
import re
import random

script, num_cores = argv

DEBUG_MODE = 0
DETAILED_MODE = 1
FULL_STATS = 0

#Latency values
L_HIT = 1
L_DRAM = 50
L_C2C = 10

# print_directory()
#
# Prints a given directory
#
def print_directory(direct):
	for i in sorted(direct):
		print i
		for j in sorted(direct[i]):
			print "\t",
			print(j),
			print "\t",
			print direct[i][j]
	
#####

# print_stats()
#
# Prints given stats
#
def print_stats(stats):
	for i in sorted(stats):
		print i
		for j in reversed(sorted(stats[i])):
			print "\t",
			print(j),
			print "\t",
			if j != "LOCS" and j != "PIDS":
				print stats[i][j]
			else:
				print ":"
				for k in sorted(stats[i][j]):
					print "\t\t ",
					print k
					for l in stats[i][j][k]:
						print "\t\t\t",
						print l,
						print "\t",
						print stats[i][j][k][l]
						sys.stdout.flush()	
######

# flush_buffer()
#
# Flushes the input buffer
#
def flush_buffer(buffer, PID):
	while buffer[PID]:
		protocol_stats["LC"]["data_tran"] += 1 #DRAM access - Writeback
		protocol_stats["LC"]["DRAM accesses"] += 1
		protocol_stats["LC"]["Latency"] += L_DRAM
		count["FLUSH_RAM"] += 1
		directory[buffer[PID].pop()][PID] = "I"
		
#####

# add_to_buffer()
#
# Adds a location to write buffer
#
def add_to_buffer(var, PID):
	if var in write_buffer[PID]: #Merging duplicate writes
		write_buffer[PID].remove(var)
	write_buffer[PID].append(var)
	if len(write_buffer[PID]) == 16: #Flushing if the buffer is full
		flush_buffer(write_buffer, PID)
		count["FLUSH_CAP"] += 1
		
#####

protocol_stats = {} #Per cache protocol
protocol_stats_snoopy = {} #Per cache protocol, Snoopy based

stats = {} #Per location
proc_stats = {} #Per processor
directory = {} #Central directory - Per location
proc_directory = {} #Central directory - Per Processor

last_clean_access = {} #Directory to track the last writer - Per location

caches = {} #Cache simulator - Per Processor

write_buffer = {} #Write Buffer simulator - Per Processor

###
count = {}
count["RD_I_HIT"] = 0
count["RD_I_C2C"] = 0
count["RD_I_RAM"] = 0
count["RD_N_HIT"] = 0
count["RD_N_C2C"] = 0
count["RD_N_RAM"] = 0

count["WR_I_HIT"] = 0
count["WR_I_C2C"] = 0
count["WR_I_RAM"] = 0
count["WR_N_HIT"] = 0
count["WR_N_C2C"] = 0
count["WR_N_RAM"] = 0

count["ACQ_I_HIT"] = 0
count["ACQ_I_C2C"] = 0
count["ACQ_I_RAM"] = 0
count["ACQ_N_HIT"] = 0
count["ACQ_N_C2C"] = 0
count["ACQ_N_RAM"] = 0

count["REL_I_HIT"] = 0
count["REL_I_C2C"] = 0
count["REL_I_RAM"] = 0
count["REL_N_HIT"] = 0
count["REL_N_C2C"] = 0
count["REL_N_RAM"] = 0

count["FLUSH_RAM"] = 0

count["FLUSH_CAP"] = 0
count["FLUSH_ATO"] = 0
count["FLUSH_ETC"] = 0

###

# Start reading simulation input
#
fid = open('exe_order.txt')
for line in fid:
	
	if DEBUG_MODE : print line
	pattern = re.compile("(P\d+) \: (RD|WR|ACQ|REL|FAIL_ACQ)\((.+)\)") #Pattern exampel : "P0 : RD(a)"
	PID = (pattern.search(line)).group(1)
	op = (pattern.search(line)).group(2)
	var = (pattern.search(line)).group(3)
	
	is_shared = False
	
	
	#Initialization
	if "LC" not in protocol_stats:
		protocol_stats["LC"] = {}
		protocol_stats["LC"]["recv_ctrl"] = 0
		protocol_stats["LC"]["send_ctrl"] = 0
		protocol_stats["LC"]["data_tran"] = 0
		protocol_stats["LC"]["DRAM accesses"] = 0
		protocol_stats["LC"]["Cache to cache"] = 0
		protocol_stats["LC"]["Latency"] = 0
	
	if "LC" not in protocol_stats_snoopy:
		protocol_stats_snoopy["LC"] = {}
		protocol_stats_snoopy["LC"]["recv_ctrl"] = 0
		protocol_stats_snoopy["LC"]["send_ctrl"] = 0
		protocol_stats_snoopy["LC"]["data_tran"] = 0
		protocol_stats_snoopy["LC"]["DRAM accesses"] = 0
		protocol_stats_snoopy["LC"]["Cache to cache"] = 0
		protocol_stats_snoopy["LC"]["Latency"] = 0

	if var not in stats:
		stats[var] = {}
		stats[var]["PIDS"] = {}
		stats[var]["NUM_Procs"] = 0
		stats[var]["RD"] = 0
		stats[var]["WR"] = 0
		stats[var]["ACQ"] = 0
		stats[var]["REL"] = 0
		stats[var]["FAIL_ACQ"] = 0

	if PID not in stats[var]["PIDS"]:
		stats[var]["PIDS"][PID] = {}
		stats[var]["PIDS"][PID]["RD"] = 0
		stats[var]["PIDS"][PID]["WR"] = 0
		stats[var]["PIDS"][PID]["ACQ"] = 0
		stats[var]["PIDS"][PID]["REL"] = 0
		stats[var]["PIDS"][PID]["FAIL_ACQ"] = 0
		stats[var]["NUM_Procs"] += 1

	if var not in directory:
		directory[var] = {}
	
	if PID not in caches:
		caches[PID] = []
	
	if PID not in write_buffer:
		write_buffer[PID] = []
	
	if var not in last_clean_access:
		last_clean_access[var] = 0
	######
	
	#Cache behaviour
	if var in caches[PID]:
		caches[PID].remove(var) #Uncomment for LRU/Comment for Random replacement
		caches[PID].append(var) #Uncomment for LRU/Comment for Random replacement
		pass
	else:
		if len(caches[PID]) < 256:
			caches[PID].append(var)
		else: #Capacity Miss, Evicting a cacheline
			# evict_loc_index = random.randint(0,9) #Uncomment for Random replacement
			evict_loc_index = 0 #Uncomment for LRU
			evict_loc = caches[PID][evict_loc_index]
			caches[PID].remove(evict_loc)
			caches[PID].append(var)
			#Updating directory
			if directory[evict_loc][PID] == "D": #Adding to write buffer
				add_to_buffer(evict_loc, PID)
				pass
			elif directory[evict_loc][PID] == "C":
				directory[evict_loc][PID] = "I"
				pass
			elif directory[evict_loc][PID] == "I":
				pass
			else:
				raise NameError("Invalid State")
	######
	
	#Protocol
	if op == "RD":
		stats[var]["PIDS"][PID]["RD"] += 1
		stats[var]["RD"] += 1
		if directory[var].has_key(PID):
		# try:
			if (directory[var][PID] == "D"):
				protocol_stats["LC"]["Latency"] += L_HIT
				count["RD_I_HIT"] += 1
				pass #Hit
			elif (directory[var][PID] == "C"):
				protocol_stats["LC"]["Latency"] += L_HIT
				count["RD_I_HIT"] += 1
				pass #Hit
			elif (directory[var][PID] == "I"):
				if (last_clean_access[var] and directory[var][last_clean_access[var]] != "I"):
					protocol_stats["LC"]["data_tran"] += 1 #Cache to cache - Read
					protocol_stats["LC"]["Cache to cache"] += 1
					protocol_stats["LC"]["Latency"] += L_C2C
					count["RD_I_C2C"] += 1
				else:
					protocol_stats["LC"]["data_tran"] += 1 #DRAM access - Read
					protocol_stats["LC"]["DRAM accesses"] += 1
					protocol_stats["LC"]["Latency"] += L_DRAM
					count["RD_I_RAM"] += 1
				directory[var][PID] = "C"
				last_clean_access[var] = PID
				pass #Miss
			else:
				raise NameError("Invalid State")
		else:
		# except KeyError:
			if (last_clean_access[var] and directory[var][last_clean_access[var]] != "I"):
				protocol_stats["LC"]["data_tran"] += 1 #Cache to cache - Read
				protocol_stats["LC"]["Cache to cache"] += 1
				protocol_stats["LC"]["Latency"] += L_C2C
				count["RD_N_C2C"] += 1
			else:
				protocol_stats["LC"]["data_tran"] += 1 #DRAM access - Read
				protocol_stats["LC"]["DRAM accesses"] += 1
				protocol_stats["LC"]["Latency"] += L_DRAM
				count["RD_N_RAM"] += 1
			directory[var][PID] = "C"
			last_clean_access[var] = PID
			pass #Cold Miss.


	elif op == "WR":
		stats[var]["PIDS"][PID]["WR"] += 1
		stats[var]["WR"] += 1
		if directory[var].has_key(PID):
		# try:
			if (directory[var][PID] == "D"):
				# last_clean_access[var] = PID
				protocol_stats["LC"]["Latency"] += L_HIT
				count["WR_I_HIT"] += 1
				pass #Hit
			elif (directory[var][PID] == "C"):
				directory[var][PID] = "D"
				# last_clean_access[var] = PID
				protocol_stats["LC"]["Latency"] += L_HIT
				count["WR_I_HIT"] += 1
				pass #Hit
			elif (directory[var][PID] == "I"):
				if (last_clean_access[var] and directory[var][last_clean_access[var]] != "I"):
					protocol_stats["LC"]["data_tran"] += 1 #Cache to cache - Read to write
					protocol_stats["LC"]["Cache to cache"] += 1
					protocol_stats["LC"]["Latency"] += L_C2C
					count["WR_I_C2C"] += 1
				else:
					protocol_stats["LC"]["data_tran"] += 1 #DRAM access - Read to write
					protocol_stats["LC"]["DRAM accesses"] += 1
					protocol_stats["LC"]["Latency"] += L_DRAM
					count["WR_I_RAM"] += 1
				directory[var][PID] = "D"
				last_clean_access[var] = PID
				pass #Miss.
			else:
				raise NameError("Invalid State")
		else:
		# except KeyError:
			if (last_clean_access[var] and directory[var][last_clean_access[var]] != "I"):
				protocol_stats["LC"]["data_tran"] += 1 #Cache to cache - Read to write
				protocol_stats["LC"]["Cache to cache"] += 1
				protocol_stats["LC"]["Latency"] += L_C2C
				count["WR_N_C2C"] += 1
			else:
				protocol_stats["LC"]["data_tran"] += 1 #DRAM access - Read to write
				protocol_stats["LC"]["DRAM accesses"] += 1
				protocol_stats["LC"]["Latency"] += L_DRAM
				count["WR_N_RAM"] += 1
			directory[var][PID] = "D"
			last_clean_access[var] = PID
			pass #Cold Miss.

		
	elif op == "ACQ":		
		stats[var]["PIDS"][PID]["ACQ"] += 1
		stats[var]["ACQ"] += 1
		if directory[var].has_key(PID):
		# try:
			if (directory[var][PID] == "D"):
				protocol_stats["LC"]["Latency"] += L_HIT
				count["ACQ_I_HIT"] += 1
				pass #Hit
			elif (directory[var][PID] == "C"):
				protocol_stats["LC"]["send_ctrl"] += 1
				if (last_clean_access[var] == PID or last_clean_access[var] == 0):
					protocol_stats["LC"]["Latency"] += L_HIT
					count["ACQ_I_HIT"] += 1
					pass #Hit
				else:
					directory[var][PID] == "I" #Invalidating clean line
					if (directory[var][last_clean_access[var]] == "D"):
						protocol_stats["LC"]["recv_ctrl"] += 1
						if (var in write_buffer[last_clean_access[var]]):
							flush_buffer(write_buffer, last_clean_access[var])
							pass #Flush
						else:
							add_to_buffer(var, last_clean_access[var])
							if len(write_buffer[last_clean_access[var]]) != 0:
								flush_buffer(write_buffer, last_clean_access[var])
								count["FLUSH_ETC"] += 1
							directory[var][last_clean_access[var]] = "C"
							pass #Writeback
						protocol_stats["LC"]["data_tran"] += 1 #Cache to Cache
						protocol_stats["LC"]["Cache to cache"] += 1
						protocol_stats["LC"]["Latency"] += L_C2C
						count["ACQ_I_C2C"] += 1
					elif (directory[var][last_clean_access[var]] == "C"):
						protocol_stats["LC"]["recv_ctrl"] += 1
						protocol_stats["LC"]["data_tran"] += 1 #Cache to Cache
						protocol_stats["LC"]["Cache to cache"] += 1
						protocol_stats["LC"]["Latency"] += L_C2C
						count["ACQ_I_C2C"] += 1
					elif (directory[var][last_clean_access[var]] == "I"):
						protocol_stats["LC"]["recv_ctrl"] += 1
						protocol_stats["LC"]["data_tran"] += 1 #DRAM access - Read
						protocol_stats["LC"]["DRAM accesses"] += 1
						protocol_stats["LC"]["Latency"] += L_DRAM
						count["ACQ_I_RAM"] += 1
					else:
						raise NameError("Invalid State")
					directory[var][PID] = "C"
					pass #Hit-Invalidate-Load
			elif (directory[var][PID] == "I"):
				protocol_stats["LC"]["send_ctrl"] += 1
				if (last_clean_access[var] == PID or last_clean_access[var] == 0):
					protocol_stats["LC"]["data_tran"] += 1 #DRAM access - Read
					protocol_stats["LC"]["DRAM accesses"] += 1
					protocol_stats["LC"]["Latency"] += L_DRAM
					count["ACQ_I_RAM"] += 1
				else:
					if (directory[var][last_clean_access[var]] == "D"):
						protocol_stats["LC"]["recv_ctrl"] += 1
						if (var in write_buffer[last_clean_access[var]]):
							flush_buffer(write_buffer, last_clean_access[var])
							pass #Flush
						else:
							add_to_buffer(var, last_clean_access[var])
							if len(write_buffer[last_clean_access[var]]) != 0:
								flush_buffer(write_buffer, last_clean_access[var])
								count["FLUSH_ETC"] += 1
							directory[var][last_clean_access[var]] = "C"
							pass #Writeback
						protocol_stats["LC"]["data_tran"] += 1 #Cache to Cache
						protocol_stats["LC"]["Cache to cache"] += 1
						protocol_stats["LC"]["Latency"] += L_C2C
						count["ACQ_I_C2C"] += 1
					elif (directory[var][last_clean_access[var]] == "C"):
						protocol_stats["LC"]["recv_ctrl"] += 1
						protocol_stats["LC"]["data_tran"] += 1 #Cache to Cache
						protocol_stats["LC"]["Cache to cache"] += 1
						protocol_stats["LC"]["Latency"] += L_C2C
						count["ACQ_I_C2C"] += 1
					elif (directory[var][last_clean_access[var]] == "I"):
						protocol_stats["LC"]["recv_ctrl"] += 1
						protocol_stats["LC"]["data_tran"] += 1 #DRAM access - Read
						protocol_stats["LC"]["DRAM accesses"] += 1
						protocol_stats["LC"]["Latency"] += L_DRAM
						count["ACQ_I_RAM"] += 1
					else:
						raise NameError("Invalid State")
				directory[var][PID] = "C"
				pass #Miss
		else:
		# except KeyError:
			protocol_stats["LC"]["send_ctrl"] += 1
			if (last_clean_access[var] == PID or last_clean_access[var] == 0):
				protocol_stats["LC"]["data_tran"] += 1 #DRAM access - Read
				protocol_stats["LC"]["DRAM accesses"] += 1
				protocol_stats["LC"]["Latency"] += L_DRAM
				count["ACQ_N_RAM"] += 1
			else:
				if (directory[var][last_clean_access[var]] == "D"):
					protocol_stats["LC"]["recv_ctrl"] += 1
					if (var in write_buffer[last_clean_access[var]]):
						flush_buffer(write_buffer, last_clean_access[var])
						pass #Flush
					else:
						add_to_buffer(var, last_clean_access[var])
						if len(write_buffer[last_clean_access[var]]) != 0:
							flush_buffer(write_buffer, last_clean_access[var])
							count["FLUSH_ETC"] += 1
						directory[var][last_clean_access[var]] = "C"
						pass #Writeback
					protocol_stats["LC"]["data_tran"] += 1 #Cache to Cache
					protocol_stats["LC"]["Cache to cache"] += 1
					protocol_stats["LC"]["Latency"] += L_C2C
					count["ACQ_N_C2C"] += 1
				elif (directory[var][last_clean_access[var]] == "C"):
					protocol_stats["LC"]["recv_ctrl"] += 1
					protocol_stats["LC"]["data_tran"] += 1 #Cache to Cache
					protocol_stats["LC"]["Cache to cache"] += 1
					protocol_stats["LC"]["Latency"] += L_C2C
					count["ACQ_N_C2C"] += 1
				elif (directory[var][last_clean_access[var]] == "I"):
					protocol_stats["LC"]["recv_ctrl"] += 1
					protocol_stats["LC"]["data_tran"] += 1 #DRAM access - Read
					protocol_stats["LC"]["DRAM accesses"] += 1
					protocol_stats["LC"]["Latency"] += L_DRAM
					count["ACQ_N_RAM"] += 1
				else:
					raise NameError("Invalid State")
			directory[var][PID] = "C"
			pass #Cold Miss
		
		#Writing to the location
		directory[var][PID] = "D"

		
	elif op == "REL":
		stats[var]["PIDS"][PID]["REL"] += 1
		stats[var]["REL"] += 1
		if directory[var].has_key(PID):
		# try:
			if (directory[var][PID] == "D"):
				protocol_stats["LC"]["Latency"] += L_HIT
				count["REL_I_HIT"] += 1
				pass #Hit
			elif (directory[var][PID] == "C"):
				directory[var][PID] = "D"
				protocol_stats["LC"]["Latency"] += L_HIT
				count["REL_I_HIT"] += 1
				pass #Hit
			elif (directory[var][PID] == "I"):
				directory[var][PID] = "D"
				protocol_stats["LC"]["data_tran"] += 1 #DRAM access - Read
				protocol_stats["LC"]["DRAM accesses"] += 1
				protocol_stats["LC"]["Latency"] += L_DRAM
				count["REL_I_RAM"] += 1
				pass #Miss.
			else:
				raise NameError("Invalid State")
		else:
		# except KeyError:
			directory[var][PID] = "D"
			protocol_stats["LC"]["data_tran"] += 1 #DRAM access - Read
			protocol_stats["LC"]["DRAM accesses"] += 1
			protocol_stats["LC"]["Latency"] += L_DRAM
			count["REL_N_RAM"] += 1
			pass #Cold Miss.
		
		#Updating the recent releaser on this location
		last_clean_access[var] = PID
		protocol_stats["LC"]["send_ctrl"] += 1

		
	elif op == "FAIL_ACQ":
		stats[var]["PIDS"][PID]["FAIL_ACQ"] += 1
		stats[var]["FAIL_ACQ"] += 1
		pass #FAIL_ACQ


	else:
		raise NameError("Check input files, Invalid operation")
	
	if DEBUG_MODE :
		print "Printing per location directory"
		print_directory(directory)
		print "-------------\n"
	
	if FULL_STATS :
		#Updating per processor Directoreis
		for location in directory:
			for proc in directory[location]:
				try:
					proc_directory[proc][location] = directory[location][proc]
				except KeyError:
					proc_directory[proc] = {}
					proc_directory[proc][location] = directory[location][proc]
	
	if DEBUG_MODE :
		print "Printing per processor directory"
		print_directory(proc_directory)
		print "\n-------------"
		print "-------------\n"

#Updating results for snoopy protocol
protocol_stats_snoopy["LC"]["send_ctrl"] = protocol_stats["LC"]["send_ctrl"]
protocol_stats_snoopy["LC"]["recv_ctrl"] = protocol_stats["LC"]["send_ctrl"]*(int(num_cores)-1)
protocol_stats_snoopy["LC"]["data_tran"] = protocol_stats["LC"]["data_tran"]
protocol_stats_snoopy["LC"]["DRAM accesses"] = protocol_stats["LC"]["DRAM accesses"]
protocol_stats_snoopy["LC"]["Cache to cache"] = protocol_stats["LC"]["Cache to cache"]
protocol_stats_snoopy["LC"]["Latency"] = protocol_stats["LC"]["Latency"]

if FULL_STATS :
	#Updating per processor stats
	for location in stats:
		for proc in stats[location]["PIDS"]:
			if proc_stats.has_key(proc):
			#try:
				if proc_stats[proc]["LOCS"].has_key(location):
					proc_stats[proc]["LOCS"][location]["RD"] = stats[location]["PIDS"][proc]["RD"]
					proc_stats[proc]["LOCS"][location]["WR"] = stats[location]["PIDS"][proc]["WR"]
					proc_stats[proc]["LOCS"][location]["ACQ"] = stats[location]["PIDS"][proc]["ACQ"]
					proc_stats[proc]["LOCS"][location]["REL"] = stats[location]["PIDS"][proc]["REL"]
					proc_stats[proc]["LOCS"][location]["FAIL_ACQ"] = stats[location]["PIDS"][proc]["FAIL_ACQ"]
				else:
					proc_stats[proc]["NUM_Locs"] += 1
					proc_stats[proc]["LOCS"][location] = {}
					proc_stats[proc]["LOCS"][location]["RD"] = stats[location]["PIDS"][proc]["RD"]
					proc_stats[proc]["LOCS"][location]["WR"] = stats[location]["PIDS"][proc]["WR"]
					proc_stats[proc]["LOCS"][location]["ACQ"] = stats[location]["PIDS"][proc]["ACQ"]
					proc_stats[proc]["LOCS"][location]["REL"] = stats[location]["PIDS"][proc]["REL"]
					proc_stats[proc]["LOCS"][location]["FAIL_ACQ"] = stats[location]["PIDS"][proc]["FAIL_ACQ"]
					
			else:
			#except KeyError:
				proc_stats[proc] = {}
				proc_stats[proc]["LOCS"] = {}
				proc_stats[proc]["NUM_Locs"] = 0
				proc_stats[proc]["RD"] = 0
				proc_stats[proc]["WR"] = 0
				proc_stats[proc]["ACQ"] = 0
				proc_stats[proc]["REL"] = 0
				proc_stats[proc]["FAIL_ACQ"] = 0
				if proc_stats[proc]["LOCS"].has_key(location):
					proc_stats[proc]["LOCS"][location]["RD"] = stats[location]["PIDS"][proc]["RD"]
					proc_stats[proc]["LOCS"][location]["WR"] = stats[location]["PIDS"][proc]["WR"]
					proc_stats[proc]["LOCS"][location]["ACQ"] = stats[location]["PIDS"][proc]["ACQ"]
					proc_stats[proc]["LOCS"][location]["REL"] = stats[location]["PIDS"][proc]["REL"]
					proc_stats[proc]["LOCS"][location]["FAIL_ACQ"] = stats[location]["PIDS"][proc]["FAIL_ACQ"]
				else:
					proc_stats[proc]["NUM_Locs"] += 1
					proc_stats[proc]["LOCS"][location] = {}
					proc_stats[proc]["LOCS"][location]["RD"] = stats[location]["PIDS"][proc]["RD"]
					proc_stats[proc]["LOCS"][location]["WR"] = stats[location]["PIDS"][proc]["WR"]
					proc_stats[proc]["LOCS"][location]["ACQ"] = stats[location]["PIDS"][proc]["ACQ"]
					proc_stats[proc]["LOCS"][location]["REL"] = stats[location]["PIDS"][proc]["REL"]
					proc_stats[proc]["LOCS"][location]["FAIL_ACQ"] = stats[location]["PIDS"][proc]["FAIL_ACQ"]
	#Updating total number of read and writes
	for proc in proc_stats:
		for location in proc_stats[proc]["LOCS"]:
			proc_stats[proc]["RD"] += proc_stats[proc]["LOCS"][location]["RD"]
			proc_stats[proc]["WR"] += proc_stats[proc]["LOCS"][location]["WR"]
			proc_stats[proc]["ACQ"] += proc_stats[proc]["LOCS"][location]["ACQ"]
			proc_stats[proc]["REL"] += proc_stats[proc]["LOCS"][location]["REL"]
			proc_stats[proc]["FAIL_ACQ"] += proc_stats[proc]["LOCS"][location]["FAIL_ACQ"]

if DEBUG_MODE :
	print "Printing per location stats"
	print_stats(stats)
	print "\n-------------\n"
	print "Printing per processor stats"
	print_stats(proc_stats)
	print "\n-------------"
	print "-------------\n"

print_directory(protocol_stats)

#Writing the results
output="LC,"
for i in sorted(protocol_stats["LC"]):
	output+=str(protocol_stats["LC"][i]) + ","
output+=str(protocol_stats_snoopy["LC"]["recv_ctrl"]) + ","
output+=str(protocol_stats_snoopy["LC"]["send_ctrl"]) + ","
if DETAILED_MODE :
	for item in sorted(count):
		output+= str(count[item]) + ","
output+="\n"
target = open("Result.csv", 'a')
target.write(output)
target.close()
