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
		protocol_stats["MESIF"]["data_tran"] += 1 #DRAM access - Writeback
		protocol_stats["MESIF"]["DRAM accesses"] += 1
		protocol_stats["MESIF"]["Latency"] += L_DRAM
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
	F_Flag = False
	
	#Initialization
	if "MESIF" not in protocol_stats:
		protocol_stats["MESIF"] = {}
		protocol_stats["MESIF"]["recv_ctrl"] = 0
		protocol_stats["MESIF"]["send_ctrl"] = 0
		protocol_stats["MESIF"]["data_tran"] = 0
		protocol_stats["MESIF"]["DRAM accesses"] = 0
		protocol_stats["MESIF"]["Cache to cache"] = 0
		protocol_stats["MESIF"]["Latency"] = 0
	
	if "MESIF" not in protocol_stats_snoopy:
		protocol_stats_snoopy["MESIF"] = {}
		protocol_stats_snoopy["MESIF"]["recv_ctrl"] = 0
		protocol_stats_snoopy["MESIF"]["send_ctrl"] = 0
		protocol_stats_snoopy["MESIF"]["data_tran"] = 0
		protocol_stats_snoopy["MESIF"]["DRAM accesses"] = 0
		protocol_stats_snoopy["MESIF"]["Cache to cache"] = 0
		protocol_stats_snoopy["MESIF"]["Latency"] = 0

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
			if directory[evict_loc][PID] == "M": #Adding to write buffer
				add_to_buffer(evict_loc, PID)
				pass
			elif directory[evict_loc][PID] == "E":
				directory[evict_loc][PID] = "I"
				pass
			elif directory[evict_loc][PID] == "S":
				directory[evict_loc][PID] = "I"
				pass
			elif directory[evict_loc][PID] == "F":
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
			if (directory[var][PID] == "M"):
				protocol_stats["MESIF"]["Latency"] += L_HIT
				count["RD_I_HIT"] += 1
				pass #Hit
			elif (directory[var][PID] == "E"):
				protocol_stats["MESIF"]["Latency"] += L_HIT
				count["RD_I_HIT"] += 1
				pass #Hit
			elif (directory[var][PID] == "S"):
				protocol_stats["MESIF"]["Latency"] += L_HIT
				count["RD_I_HIT"] += 1
				pass #Hit
			elif (directory[var][PID] == "F"):
				protocol_stats["MESIF"]["Latency"] += L_HIT
				count["RD_I_HIT"] += 1
				pass #Hit
			elif (directory[var][PID] == "I"):
				protocol_stats["MESIF"]["send_ctrl"] += 1
				for proc in directory[var]:
					if (proc != PID and directory[var][proc] != "I"):
						if (directory[var][proc] == "M"):
							protocol_stats["MESIF"]["recv_ctrl"] += 1
							if var in write_buffer[proc]:
								flush_buffer(write_buffer, proc)
								pass #Flush
							else:
								add_to_buffer(var, proc)
								if len(write_buffer[proc]) != 0:
									flush_buffer(write_buffer, proc)
									count["FLUSH_ETC"] += 1
								is_shared = True
								directory[var][proc] = "S"
								pass #M-->S, Write back.
							pass #Control Message
						elif (directory[var][proc] == "E"):
							is_shared = True
							directory[var][proc] = "S"
							protocol_stats["MESIF"]["recv_ctrl"] += 1
							pass #E-->S, Control Message
						elif (directory[var][proc] == "S"):
							is_shared = True
							protocol_stats["MESIF"]["recv_ctrl"] += 1
							pass #Control Message
						elif (directory[var][proc] == "F"):
							is_shared = True
							directory[var][proc] = "S"
							protocol_stats["MESIF"]["recv_ctrl"] += 1
							F_Flag = True
							pass #Control Message
						else:
							raise NameError("Invalid State")
				if(is_shared):
					directory[var][PID] = "F"
					protocol_stats["MESIF"]["data_tran"] += 1
					if(F_Flag):
						protocol_stats["MESIF"]["Cache to cache"] += 1 #Cache to Cache
						protocol_stats["MESIF"]["Latency"] += L_C2C
						count["RD_I_C2C"] += 1
					else:
						protocol_stats["MESIF"]["DRAM accesses"] += 1
						protocol_stats["MESIF"]["Latency"] += L_DRAM
						count["RD_I_RAM"] += 1
					pass #Miss
				else:
					directory[var][PID] = "E"
					protocol_stats["MESIF"]["data_tran"] += 1
					protocol_stats["MESIF"]["DRAM accesses"] += 1 #DRAM access - Read
					protocol_stats["MESIF"]["Latency"] += L_DRAM
					count["RD_I_RAM"] += 1
					pass #Miss
			else:
				raise NameError("Invalid State")
		else:
		# except KeyError:
			protocol_stats["MESIF"]["send_ctrl"] += 1
			for proc in directory[var]:
				if (proc != PID and directory[var][proc] != "I"):
					if (directory[var][proc] == "M"):
						protocol_stats["MESIF"]["recv_ctrl"] += 1
						if var in write_buffer[proc]:
							flush_buffer(write_buffer, proc)
							pass #Flush
						else:
							add_to_buffer(var, proc)
							if len(write_buffer[proc]) != 0:
								flush_buffer(write_buffer, proc)
								count["FLUSH_ETC"] += 1
							is_shared = True
							directory[var][proc] = "S"
							pass #M-->S, Write back.
						pass #Control Message
					elif (directory[var][proc] == "E"):
						is_shared = True
						directory[var][proc] = "S"
						protocol_stats["MESIF"]["recv_ctrl"] += 1
						pass #E-->S, Control Message
					elif (directory[var][proc] == "S"):
						is_shared = True
						protocol_stats["MESIF"]["recv_ctrl"] += 1
						pass #Control Message
					elif (directory[var][proc] == "F"):
						is_shared = True
						directory[var][proc] = "S"
						protocol_stats["MESIF"]["recv_ctrl"] += 1
						F_Flag = True
						pass #Control Message
					else:
						raise NameError("Invalid State")
			if(is_shared):
				directory[var][PID] = "F"
				protocol_stats["MESIF"]["data_tran"] += 1
				if(F_Flag):
					protocol_stats["MESIF"]["Cache to cache"] += 1 #Cache to Cache
					protocol_stats["MESIF"]["Latency"] += L_C2C
					count["RD_N_C2C"] += 1
				else:
					protocol_stats["MESIF"]["DRAM accesses"] += 1
					protocol_stats["MESIF"]["Latency"] += L_DRAM
					count["RD_N_RAM"] += 1
				pass #Cold Miss
			else:
				directory[var][PID] = "E"
				protocol_stats["MESIF"]["data_tran"] += 1
				protocol_stats["MESIF"]["DRAM accesses"] += 1 #DRAM access - Read
				protocol_stats["MESIF"]["Latency"] += L_DRAM
				count["RD_N_RAM"] += 1
				pass #Cold Miss


	elif op == "WR":
		stats[var]["PIDS"][PID]["WR"] += 1
		stats[var]["WR"] += 1
		if directory[var].has_key(PID):
		# try:
			if (directory[var][PID] == "M"):
				protocol_stats["MESIF"]["Latency"] += L_HIT
				count["WR_I_HIT"] += 1
				pass #Hit
			elif (directory[var][PID] == "E"):
				directory[var][PID] = "M"
				protocol_stats["MESIF"]["Latency"] += L_HIT
				count["WR_I_HIT"] += 1
				pass #Hit
			elif (directory[var][PID] == "S"):
				directory[var][PID] = "M"
				protocol_stats["MESIF"]["Latency"] += L_HIT
				count["WR_I_HIT"] += 1
				protocol_stats["MESIF"]["send_ctrl"] += 1
				for proc in directory[var]:
					if (proc != PID and directory[var][proc] != "I"):
						protocol_stats["MESIF"]["recv_ctrl"] += 1
						directory[var][proc] = "I"
						pass #Invalidating others
				pass #Hit, Contorl Message
			elif (directory[var][PID] == "F"):
				directory[var][PID] = "M"
				protocol_stats["MESIF"]["Latency"] += L_HIT
				count["WR_I_HIT"] += 1
				protocol_stats["MESIF"]["send_ctrl"] += 1
				for proc in directory[var]:
					if (proc != PID and directory[var][proc] != "I"):
						protocol_stats["MESIF"]["recv_ctrl"] += 1
						directory[var][proc] = "I"
						pass #Invalidating others
				pass #Hit, Contorl Message
			elif (directory[var][PID] == "I"):
				protocol_stats["MESIF"]["send_ctrl"] += 1
				for proc in directory[var]:
					if (proc != PID and directory[var][proc] != "I"):
						if (directory[var][proc] == "M"):
							protocol_stats["MESIF"]["recv_ctrl"] += 1
							if var in write_buffer[proc]:
								flush_buffer(write_buffer, proc)
								pass #Flush
							else:
								add_to_buffer(var, proc)
								if len(write_buffer[proc]) != 0:
									flush_buffer(write_buffer, proc)
									count["FLUSH_ETC"] += 1
								pass #Invalidating others, Write back.
							pass #Control Message
						elif (directory[var][proc] == "E"):
							directory[var][proc] = "I"
							protocol_stats["MESIF"]["recv_ctrl"] += 1
							pass #Invalidating others, Contorl Message
						elif (directory[var][proc] == "S"):
							directory[var][proc] = "I"
							protocol_stats["MESIF"]["recv_ctrl"] += 1
							pass #Invalidating others, Contorl Message
						elif (directory[var][proc] == "F"):
							directory[var][proc] = "I"
							protocol_stats["MESIF"]["recv_ctrl"] += 1
							F_Flag = True
							pass #Invalidating others, Contorl Message
						else:
							raise NameError("Invalid State")
				directory[var][PID] = "M"
				if(F_Flag):
					protocol_stats["MESIF"]["data_tran"] += 1
					protocol_stats["MESIF"]["Cache to cache"] += 1 #Cache to Cache
					protocol_stats["MESIF"]["Latency"] += L_C2C
					count["WR_I_C2C"] += 1
					pass #Miss.
				else:
					protocol_stats["MESIF"]["data_tran"] += 1
					protocol_stats["MESIF"]["DRAM accesses"] += 1 #DRAM access - Read
					protocol_stats["MESIF"]["Latency"] += L_DRAM
					count["WR_I_RAM"] += 1
					pass #Miss.
			else:
				raise NameError("Invalid State")
		else:
		# except KeyError:
			protocol_stats["MESIF"]["send_ctrl"] += 1
			for proc in directory[var]:
				if (proc != PID and directory[var][proc] != "I"):
					if (directory[var][proc] == "M"):
						protocol_stats["MESIF"]["recv_ctrl"] += 1
						if var in write_buffer[proc]:
							flush_buffer(write_buffer, proc)
							pass #Flush
						else:
							add_to_buffer(var, proc)
							if len(write_buffer[proc]) != 0:
								flush_buffer(write_buffer, proc)
								count["FLUSH_ETC"] += 1
							pass #Invalidating others, Write back.
						pass #Control Message
					elif (directory[var][proc] == "E"):
						directory[var][proc] = "I"
						protocol_stats["MESIF"]["recv_ctrl"] += 1
						pass #Invalidating others, Contorl Message
					elif (directory[var][proc] == "S"):
						directory[var][proc] = "I"
						protocol_stats["MESIF"]["recv_ctrl"] += 1
						pass #Invalidating others, Contorl Message
					elif (directory[var][proc] == "F"):
						directory[var][proc] = "I"
						protocol_stats["MESIF"]["recv_ctrl"] += 1
						F_Flag = True
						pass #Invalidating others, Contorl Message
					else:
						raise NameError("Invalid State")
			directory[var][PID] = "M"
			if(F_Flag):
				protocol_stats["MESIF"]["data_tran"] += 1
				protocol_stats["MESIF"]["Cache to cache"] += 1 #Cache to Cache
				protocol_stats["MESIF"]["Latency"] += L_C2C
				count["WR_N_C2C"] += 1
				pass #Cold Miss.
			else:
				protocol_stats["MESIF"]["data_tran"] += 1
				protocol_stats["MESIF"]["DRAM accesses"] += 1 #DRAM access - Read
				protocol_stats["MESIF"]["Latency"] += L_DRAM
				count["WR_N_RAM"] += 1
				pass #Cold Miss.

		
	elif op == "ACQ":
		stats[var]["PIDS"][PID]["ACQ"] += 1
		stats[var]["ACQ"] += 1
		
		#Flushing all the write buffers
		protocol_stats["MESIF"]["send_ctrl"] += 1
		for proc in directory[var]:
			#if var in write_buffer[proc]:
			protocol_stats["MESIF"]["recv_ctrl"] += 1
			flush_buffer(write_buffer, proc)
			pass #Flush
		
		if directory[var].has_key(PID):
		# try:
			if (directory[var][PID] == "M"):
				protocol_stats["MESIF"]["Latency"] += L_HIT
				count["ACQ_I_HIT"] += 1
				pass #Hit
			elif (directory[var][PID] == "E"):
				directory[var][PID] = "M"
				protocol_stats["MESIF"]["Latency"] += L_HIT
				count["ACQ_I_HIT"] += 1
				pass #Hit
			elif (directory[var][PID] == "S"):
				directory[var][PID] = "M"
				protocol_stats["MESIF"]["Latency"] += L_HIT
				count["ACQ_I_HIT"] += 1
				protocol_stats["MESIF"]["send_ctrl"] += 1
				for proc in directory[var]:
					if (proc != PID and directory[var][proc] != "I"):
						protocol_stats["MESIF"]["recv_ctrl"] += 1
						directory[var][proc] = "I"
						pass #Invalidating others
				pass #Hit, Contorl Message
			elif (directory[var][PID] == "F"):
				directory[var][PID] = "M"
				protocol_stats["MESIF"]["Latency"] += L_HIT
				count["ACQ_I_HIT"] += 1
				protocol_stats["MESIF"]["send_ctrl"] += 1
				for proc in directory[var]:
					if (proc != PID and directory[var][proc] != "I"):
						protocol_stats["MESIF"]["recv_ctrl"] += 1
						directory[var][proc] = "I"
						pass #Invalidating others
				pass #Hit, Contorl Message
			elif (directory[var][PID] == "I"):
				protocol_stats["MESIF"]["send_ctrl"] += 1
				for proc in directory[var]:
					if (proc != PID and directory[var][proc] != "I"):
						if (directory[var][proc] == "M"):
							protocol_stats["MESIF"]["recv_ctrl"] += 1
							if var in write_buffer[proc]:
								flush_buffer(write_buffer, proc)
								pass #Flush
							else:
								add_to_buffer(var, proc)
								if len(write_buffer[proc]) != 0:
									flush_buffer(write_buffer, proc)
									count["FLUSH_ETC"] += 1
								pass #Invalidating others, Write back.
							pass #Control Message
						elif (directory[var][proc] == "E"):
							directory[var][proc] = "I"
							protocol_stats["MESIF"]["recv_ctrl"] += 1
							pass #Invalidating others, Contorl Message
						elif (directory[var][proc] == "S"):
							directory[var][proc] = "I"
							protocol_stats["MESIF"]["recv_ctrl"] += 1
							pass #Invalidating others, Contorl Message
						elif (directory[var][proc] == "F"):
							directory[var][proc] = "I"
							protocol_stats["MESIF"]["recv_ctrl"] += 1
							F_Flag = True
							pass #Invalidating others, Contorl Message
						else:
							raise NameError("Invalid State")
				directory[var][PID] = "M"
				if(F_Flag):
					protocol_stats["MESIF"]["data_tran"] += 1
					protocol_stats["MESIF"]["Cache to cache"] += 1 #Cache to Cache
					protocol_stats["MESIF"]["Latency"] += L_C2C
					count["ACQ_I_C2C"] += 1
					pass #Miss.
				else:
					protocol_stats["MESIF"]["data_tran"] += 1
					protocol_stats["MESIF"]["DRAM accesses"] += 1 #DRAM access - Read
					protocol_stats["MESIF"]["Latency"] += L_DRAM
					count["ACQ_I_RAM"] += 1
					pass #Miss.
			else:
				raise NameError("Invalid State")
		else:
		# except KeyError:
			protocol_stats["MESIF"]["send_ctrl"] += 1
			for proc in directory[var]:
				if (proc != PID and directory[var][proc] != "I"):
					if (directory[var][proc] == "M"):
						protocol_stats["MESIF"]["recv_ctrl"] += 1
						if var in write_buffer[proc]:
							flush_buffer(write_buffer, proc)
							pass #Flush
						else:
							add_to_buffer(var, proc)
							if len(write_buffer[proc]) != 0:
								flush_buffer(write_buffer, proc)
								count["FLUSH_ETC"] += 1
							pass #Invalidating others, Write back.
						pass #Control Message
					elif (directory[var][proc] == "E"):
						directory[var][proc] = "I"
						protocol_stats["MESIF"]["recv_ctrl"] += 1
						pass #Invalidating others, Contorl Message
					elif (directory[var][proc] == "S"):
						directory[var][proc] = "I"
						protocol_stats["MESIF"]["recv_ctrl"] += 1
						pass #Invalidating others, Contorl Message
					elif (directory[var][proc] == "F"):
						directory[var][proc] = "I"
						protocol_stats["MESIF"]["recv_ctrl"] += 1
						F_Flag = True
						pass #Invalidating others, Contorl Message
					else:
						raise NameError("Invalid State")
			directory[var][PID] = "M"
			if(F_Flag):
				protocol_stats["MESIF"]["data_tran"] += 1
				protocol_stats["MESIF"]["Cache to cache"] += 1 #Cache to Cache
				protocol_stats["MESIF"]["Latency"] += L_C2C
				count["ACQ_N_C2C"] += 1
				pass #Cold Miss.
			else:
				protocol_stats["MESIF"]["data_tran"] += 1
				protocol_stats["MESIF"]["DRAM accesses"] += 1 #DRAM access - Read
				protocol_stats["MESIF"]["Latency"] += L_DRAM
				count["ACQ_N_RAM"] += 1
				pass #Cold Miss.

		
	elif op == "REL":
		if directory[var].has_key(PID):
		# try:
			if (directory[var][PID] == "M"):
				protocol_stats["MESIF"]["Latency"] += L_HIT
				count["REL_I_HIT"] += 1
				pass #Hit
			elif (directory[var][PID] == "E"):
				directory[var][PID] = "M"
				protocol_stats["MESIF"]["Latency"] += L_HIT
				count["REL_I_HIT"] += 1
				pass #Hit
			elif (directory[var][PID] == "S"):
				directory[var][PID] = "M"
				protocol_stats["MESIF"]["Latency"] += L_HIT
				count["REL_I_HIT"] += 1
				protocol_stats["MESIF"]["send_ctrl"] += 1
				for proc in directory[var]:
					if (proc != PID and directory[var][proc] != "I"):
						protocol_stats["MESIF"]["recv_ctrl"] += 1
						directory[var][proc] = "I"
						pass #Invalidating others
				pass #Hit, Contorl Message
			elif (directory[var][PID] == "F"):
				directory[var][PID] = "M"
				protocol_stats["MESIF"]["Latency"] += L_HIT
				count["REL_I_HIT"] += 1
				protocol_stats["MESIF"]["send_ctrl"] += 1
				for proc in directory[var]:
					if (proc != PID and directory[var][proc] != "I"):
						protocol_stats["MESIF"]["recv_ctrl"] += 1
						directory[var][proc] = "I"
						pass #Invalidating others
				pass #Hit, Contorl Message
			elif (directory[var][PID] == "I"):
				protocol_stats["MESIF"]["send_ctrl"] += 1
				for proc in directory[var]:
					if (proc != PID and directory[var][proc] != "I"):
						if (directory[var][proc] == "M"):
							protocol_stats["MESIF"]["recv_ctrl"] += 1
							if var in write_buffer[proc]:
								flush_buffer(write_buffer, proc)
								pass #Flush
							else:
								add_to_buffer(var, proc)
								if len(write_buffer[proc]) != 0:
									flush_buffer(write_buffer, proc)
									count["FLUSH_ETC"] += 1
								pass #Invalidating others, Write back.
							pass #Control Message
						elif (directory[var][proc] == "E"):
							directory[var][proc] = "I"
							protocol_stats["MESIF"]["recv_ctrl"] += 1
							pass #Invalidating others, Contorl Message
						elif (directory[var][proc] == "S"):
							directory[var][proc] = "I"
							protocol_stats["MESIF"]["recv_ctrl"] += 1
							pass #Invalidating others, Contorl Message
						elif (directory[var][proc] == "F"):
							directory[var][proc] = "I"
							protocol_stats["MESIF"]["recv_ctrl"] += 1
							F_Flag = True
							pass #Invalidating others, Contorl Message
						else:
							raise NameError("Invalid State")
				directory[var][PID] = "M"
				if(F_Flag):
					protocol_stats["MESIF"]["data_tran"] += 1
					protocol_stats["MESIF"]["Cache to cache"] += 1 #Cache to Cache
					protocol_stats["MESIF"]["Latency"] += L_C2C
					count["REL_I_C2C"] += 1
					pass #Miss.
				else:
					protocol_stats["MESIF"]["data_tran"] += 1
					protocol_stats["MESIF"]["DRAM accesses"] += 1 #DRAM access - Read
					protocol_stats["MESIF"]["Latency"] += L_DRAM
					count["REL_I_RAM"] += 1
					pass #Miss.
			else:
				raise NameError("Invalid State")
		else:
		# except KeyError:
			protocol_stats["MESIF"]["send_ctrl"] += 1
			for proc in directory[var]:
				if (proc != PID and directory[var][proc] != "I"):
					if (directory[var][proc] == "M"):
						protocol_stats["MESIF"]["recv_ctrl"] += 1
						if var in write_buffer[proc]:
							flush_buffer(write_buffer, proc)
							pass #Flush
						else:
							add_to_buffer(var, proc)
							if len(write_buffer[proc]) != 0:
								flush_buffer(write_buffer, proc)
								count["FLUSH_ETC"] += 1
							pass #Invalidating others, Write back.
						pass #Control Message
					elif (directory[var][proc] == "E"):
						directory[var][proc] = "I"
						protocol_stats["MESIF"]["recv_ctrl"] += 1
						pass #Invalidating others, Contorl Message
					elif (directory[var][proc] == "S"):
						directory[var][proc] = "I"
						protocol_stats["MESIF"]["recv_ctrl"] += 1
						pass #Invalidating others, Contorl Message
					elif (directory[var][proc] == "F"):
						directory[var][proc] = "I"
						protocol_stats["MESIF"]["recv_ctrl"] += 1
						F_Flag = True
						pass #Invalidating others, Contorl Message
					else:
						raise NameError("Invalid State")
			directory[var][PID] = "M"
			if(F_Flag):
				protocol_stats["MESIF"]["data_tran"] += 1
				protocol_stats["MESIF"]["Cache to cache"] += 1 #Cache to Cache
				protocol_stats["MESIF"]["Latency"] += L_C2C
				count["REL_N_C2C"] += 1
				pass #Cold Miss.
			else:
				protocol_stats["MESIF"]["data_tran"] += 1
				protocol_stats["MESIF"]["DRAM accesses"] += 1 #DRAM access - Read
				protocol_stats["MESIF"]["Latency"] += L_DRAM
				count["REL_N_RAM"] += 1
				pass #Cold Miss.

		
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
protocol_stats_snoopy["MESIF"]["send_ctrl"] = protocol_stats["MESIF"]["send_ctrl"]
protocol_stats_snoopy["MESIF"]["recv_ctrl"] = protocol_stats["MESIF"]["send_ctrl"]*(int(num_cores)-1)
protocol_stats_snoopy["MESIF"]["data_tran"] = protocol_stats["MESIF"]["data_tran"]
protocol_stats_snoopy["MESIF"]["DRAM accesses"] = protocol_stats["MESIF"]["DRAM accesses"]
protocol_stats_snoopy["MESIF"]["Cache to cache"] = protocol_stats["MESIF"]["Cache to cache"]
protocol_stats_snoopy["MESIF"]["Latency"] = protocol_stats["MESIF"]["Latency"]

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
output="MESIF,"
for i in sorted(protocol_stats["MESIF"]):
	output+=str(protocol_stats["MESIF"][i]) + ","
output+=str(protocol_stats_snoopy["MESIF"]["recv_ctrl"]) + ","
output+=str(protocol_stats_snoopy["MESIF"]["send_ctrl"]) + ","
if DETAILED_MODE :
	for item in sorted(count):
		output+= str(count[item]) + ","
output+="\n"
target = open("Result.csv", 'a')
target.write(output)
target.close()