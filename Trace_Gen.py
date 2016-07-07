import random
import re
from sys import argv

script, num_cores = argv

DEBUG_MODE = 0

fid = []
done = []
lock_loc = {}

for i in range(int(num_cores)):
	fid.append(open('Core%d.txt' % i, 'r').readlines())

file_name = "exe_order.txt"
target = open(file_name, 'w')

while(True):
	
	seed = (random.randint(0, int(num_cores)-1))
	while seed in done:
		seed = (random.randint(0, int(num_cores)-1))	
	
	
	if fid[seed]:
		new_line = fid[seed].pop(0)
		
		pattern = re.compile("(RD|WR|ACQ|REL)\((.+)\)") #Pattern exampel : "RD(a)"
		op = (pattern.search(new_line)).group(1)
		var = (pattern.search(new_line)).group(2)
		PID = "P%d" %seed		
		
		if (op=="ACQ"):
			if var not in lock_loc:
				lock_loc[var]=""
			if not lock_loc[var]:
				lock_loc[var]=PID
				target.write(PID + " : " + new_line)
			elif lock_loc[var]==PID:
				raise NameError("Acquiring location %s by processor %s for the second time" %(var ,PID))
			else:
				fid[seed].insert(0,new_line)
				target.write(PID + " : FAIL_" + new_line)
				if DEBUG_MODE:
					print "FAIL_ACQ on processor %s" %PID
		elif (op=="REL"):
			if var not in lock_loc:
				raise NameError("Releasing location %s by processor %s without acquring it" %(var, PID))
			if not lock_loc[var]:
				raise NameError("Releasing location %s by processor %s without acquring it" %(var, PID))
			elif lock_loc[var]==PID:
				lock_loc[var]=""
				target.write(PID + " : " + new_line)
			else:
				raise NameError("Releasing location %s by processor %s while locaation is acquired by processor %s" %(var, PID, lock_loc[var]))
		else:		
			target.write(PID + " : " + new_line)
		
	else:
		done.append(seed)
		if len(done) == int(num_cores):
			break
		continue

#Generating output file:
output = open("Result.csv", 'w')
output.write(",Cache to cache,DRAM accesses,Latency,data_tran,recv_ctrl,send_ctrl,recv_ctrl_snoopy,send_ctrl_snoopy")
output.write(",ACQ_I_C2C,ACQ_I_HIT,ACQ_I_RAM,ACQ_N_C2C,ACQ_N_HIT,ACQ_N_RAM,FLUSH_ATO,FLUSH_CAP,FLUSH_ETC,FLUSH_RAM,RD_I_C2C,RD_I_HIT,RD_I_RAM,RD_N_C2C,RD_N_HIT,RD_N_RAM,REL_I_C2C,REL_I_HIT,REL_I_RAM,REL_N_C2C,REL_N_HIT,REL_N_RAM,WR_I_C2C,WR_I_HIT,WR_I_RAM,WR_N_C2C,WR_N_HIT,WR_N_RAM")
output.write("\n")
output.close()

print "Trace_Gen : Done!"

