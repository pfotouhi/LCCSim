import string
import random
import math
from sys import argv

script, num_cores, num_vars, num_inst, RD_WR_ratio, num_crit_sec , crit_sec_instances, size_crit_sec = argv

DEBUG_MODE = 0

# #Checking if the total number of critical sectoins is higher that total number of cores.
# if():
	# raise NameError("Number of critical sectoins is higher that number of cores.")

#Creating a dictionary to track where instances of critical sections are inserted
crit_directory ={}

#Creating a list of required number of locations (A0,B0,C0,...)
labels = []
for index in range(int(math.ceil(int(num_vars)/26.0))):
	for letter in list(string.ascii_uppercase):
		labels.append(letter + str(index))


#Generating critical sections
#Creating a list for synchronization variables (a,b,c,...) - All lower case
sync_labels = []
for sync_index in range(int(math.ceil(int(num_crit_sec)/26.0))):
	for letter in list(string.ascii_lowercase):
		sync_labels.append(letter + str(sync_index))


file = []		
#Reading input files
for core in range(int(num_cores)):
	core_id = "Core%d" %core
	file_name = core_id + ".txt"
	target = open(file_name, 'r')
	file.append(target.readlines())
	target.close

for l in range(int(num_crit_sec)):

	#Generating the critical section
	critical_section = []
	sync_var = sync_labels.pop()
	line = "ACQ" + "(" + sync_var + ")\n"
	critical_section.append(line)

	for i in range(int(size_crit_sec)):
		#Choosing between RD/WR
		if ((random.randint(1, 100)) <= (1/(float(RD_WR_ratio)+1))*100):
			op = "WR"
		else:
			op = "RD"
		#Choosing the location
		x = labels[random.randint(0, int(num_vars)-1)]
		line = op + "(" + x + ")\n"
		critical_section.append(line)

	line = "REL" + "(" + sync_var + ")\n"
	critical_section.append(line)
	
	crit_directory[sync_var] = {}
	
	#Inserting instances of critical section
	for i in range(int(crit_sec_instances)):
		
		j = random.randint(0, int(num_cores)-1)
		core_id = "Core%d" %j
		file_name = core_id + ".txt"
		
		if not (crit_directory[sync_var].has_key(file_name)):
			crit_directory[sync_var][file_name] = []
		
		tmp_list = []
		Err_Flag = True
		while(Err_Flag):
			k = random.randint(0, int(num_inst)-1)
			Err_Flag = False
			for line_num in crit_directory[sync_var][file_name]:
				if (k <= line_num):
					tmp_list.append(line_num+int(size_crit_sec)+2)
				elif (line_num+int(size_crit_sec)+2 <= k):
					tmp_list.append(line_num)
				else:
					Err_Flag = True
					break
				
		
		tmp_list.append(k)
		crit_directory[sync_var][file_name] = tmp_list

		for inst in critical_section:
			file[j].insert(k, inst)
			k += 1
			
		if DEBUG_MODE:
			print file_name + " changed" + " in line" + str(k-(int(size_crit_sec)+2)) + ".\n"

#Writing input files
for core in range(int(num_cores)):
	core_id = "Core%d" %core
	file_name = core_id + ".txt"
	target = open(file_name, 'w')
	target.writelines(file[core])
	target.close
			
print "Crit_Sec_Gen : Done!"
