import string
import random
import math
from sys import argv

script, num_cores, num_vars, num_inst, RD_WR_ratio, access_percentage_option = argv

#Creating a list of required number of locations (A0,B0,C0,...)
labels = []
for index in range(int(math.ceil(int(num_vars)/26.0))):
	for letter in list(string.ascii_uppercase):
		labels.append(letter + str(index))

#Generating insturctions per core
vars = {}
for i in range(int(num_cores)):
	core_id = "Core%d" %i

	file_name = core_id + ".txt"
	target = open(file_name, 'w')

	var = iter(labels)
	if int(access_percentage_option):
		print core_id + " :"
		for k in range(int(num_vars)):
			tmp_var = var.next()
			vars[tmp_var] = int(raw_input("Enter the access percentage for variable \"%s\" :\t" %(tmp_var)))
		while sum(vars.values()) != 100 :
			print "The sum of percentages is not equal to 100, please enter valid numbers:"
			for x, y in vars.iteritems():
				vars[x] = int(raw_input("Enter the access percentage for variable \"%s\" :\t" %(x)))
	else:
		for k in range(int(num_vars)):
			tmp_var = var.next()
			vars[tmp_var] = float(100)/int(num_vars)

	L_Flag = 0
	num_WR, num_RD = 0, 0
	for j in range(int(num_inst)):
		#Choosing between RD/WR
		if ((random.randint(1, 100)) <= (1/(float(RD_WR_ratio)+1))*100):
			target.write("WR")
			num_WR += 1
		else:
			target.write("RD")
			num_RD += 1
		#Choosing the location
		tmp = random.random()*100
		for x, y in vars.iteritems():
			if (tmp <= y):
				target.write("(" + x + ")\n")
				L_Flag = 1
				break
			else:
				tmp = tmp - (y)
		if not L_Flag :
			raise NameError("Problem choosing location")
	target.close()
print "Inst_Gen : Done!"

