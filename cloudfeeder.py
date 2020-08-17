"""
This script is to collect the required data from the in-vehicle server,
pre-process them, and feed them to the KUKSA cloud.

The script needs to be located in the same directory where testclient.py 
is also located: ~/kuksa.val/vss-testclient/

Prior to running this script, the following lines should be added to 
testclient.py:
# At the end of - 'def do_getValue(self, args)'
datastore = json.loads(resp)
return datastore

"""

import time
import testclient

def checkPath(path):
	val = tclient.do_getValue(path)['value']
	if val == "---":
		return 0.0
	else:
		return float(val)

def printSignalValues(ch0_dic, ch1_dic):
	print("######################## Channel-1 ########################")
	for signal, value in ch0_dic.items():
		print(signal, ": ", str(value))
	print("######################## Channel-2 ########################")	
	for signal, value in ch1_dic.items():
		print(signal, ": ", str(value))
	print("###########################################################")

# Create a testclient instance and connect to the running vss server
tclient = testclient.VSSTestClient()
tclient.do_connect("--insecure")

# Authorize as a super-admin
super_admin_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJrdWtzYS52YWwiLCJpc3MiOiJFY2xpcHNlIEtVS1NBIERldiIsImFkbWluIjp0cnVlLCJpYXQiOjE1MTYyMzkwMjIsImV4cCI6MTYwNjIzOTAyMiwidzNjLXZzcyI6eyIqIjoicncifX0.bUcEW4o3HiBHZAdy71qCWcu9oBSZClntI1ZXq7HAM8i8nDtiUP4up-VXxt3S3n8AKJQOZVlHudP_ixGTb1HBKa3_CD0HFurP_Wf2Jnrgguhqi1sUItvGjgq4BPpuBsu9kV1Ds-JDmCPBBuHfRtCck353BmMyv6CHn2CCgVQH-DwW6k7wOqcFkxfxfkClO-nrUSQbad_MrxNHhrnflb3N8bc4r61BQ8gHiEyl7JJIuLhAb7bLgarjqcHABkw6T2TkwfWFsddMR2GL_PYBP4D3_r-2IHAhixiEiO758lxA2-o2D0jtte-KmTHjeEUpaWr-ryv1whZXnE243iV1lMajvjgWq5ZnsYTG4Ff7GsR_4SKyd9j6wInkog5Kkx5tFJr2P9kh7HupXQeUzbuoJ7lZAgpGyD8icxZg7c8VTpLzTs5zowjJwbxze5JAylWcXLXOA3vQKpn8E3MseD_31LoVZGEvD9p372IgVmJ0ui4qT8_ZHeGPc8bV2Iy0vDkdAhjf-4Lwf4rDGDksYpK_PO70KylGRmZ9TqiKqstUI6AWG50Jii8MPnnr8qyNO3FD8Rv7E8BnL8ioLoN5VI9eyxy1HpW2SfLKUuCaLB9iKd6fv4U_DhF1AS-Y-iu8-kOovxkTk801DhDxWJN0nyRwmhqn8exjikNB1jnW5mFWLTeagNA"
tclient.do_authorize(super_admin_token)

sigDictCH0 = {}
sigDictCH1 = {}
while True:
	# 1. Save signals' values from the target path signal dictionaries
	ambientAirTemp = checkPath("Vehicle.AmbientAirTemperature")
	exhaustMessFlow = checkPath("Vehicle.ExhaustMassFlow")
	barometricPress = checkPath("Vehicle.OBD.BarometricPressure")
	coolantTemp = checkPath("Vehicle.OBD.CoolantTemperature")
	loadAtCurrentSpeed = checkPath("Vehicle.OBD.EngPercentLoadAtCurrentSpeed")
	timeSinceStart = checkPath("Vehicle.Drivetrain.FuelSystem.TimeSinceStart")
	actualTorque = checkPath(
		"Vehicle.Drivetrain.InternalCombustionEngine.Engine.ActualEngPercentTorque")
	referenceTorque = checkPath(
		"Vehicle.Drivetrain.InternalCombustionEngine.Engine.EngReferenceTorque")
	nomFrictionTorque = checkPath(
		"Vehicle.Drivetrain.InternalCombustionEngine.Engine.NominalFrictionPercentTorque")
	engSpeed = checkPath(
		"Vehicle.Drivetrain.InternalCombustionEngine.Engine.Speed")
	engSpeedAtIdle = checkPath(
		"Vehicle.Drivetrain.InternalCombustionEngine.Engine.SpeedAtIdle")
	engSpeedAtKickIn = checkPath(
		"Vehicle.Drivetrain.InternalCombustionEngine.Engine.SpeedAtKickIn")
	noxIntake = checkPath(
		"Vehicle.AfterTreatment.NOxLevel.NOxIntake1")
	noxOutlet = checkPath(
		"Vehicle.AfterTreatment.NOxLevel.NOxOutlet1")
	
	# 2. Store newly retrieved data to the dictionary keys
	## A. Calculate integrated NOx mass
	sigDictCH0["Aftrtratment1ExhaustGasMassFlow"] = exhaustMessFlow
	sigDictCH1["Aftertreatment1IntakeNOx"] = noxIntake 
	sigDictCH1["Aftertreatment1OutletNOx"] = noxOutlet
	## B. Calculate engine work
	sigDictCH0["EngReferenceTorque"] = referenceTorque # Missing
	## C. Map switch over
	sigDictCH0["AmbientAirTemp"] = ambientAirTemp
	sigDictCH0["BarometricPress"] = barometricPress
	sigDictCH0["EngCoolantTemp"] = coolantTemp
	## D. Bin selection
	sigDictCH0["EngPercentLoadAtCurrentSpeed"] = loadAtCurrentSpeed
	sigDictCH0["EngSpeedAtIdlePoint1"] = engSpeedAtIdle # Missing
	sigDictCH0["EngSpeedAtPoint2"] = engSpeedAtKickIn # Missing
	## A & B & C
	sigDictCH0["EngSpeed"] = engSpeed
	## B & D
	sigDictCH0["ActualEngPercentTorque"] = actualTorque
	sigDictCH0["NominalFrictionPercentTorque"] = nomFrictionTorque
	## C - case 2 & Sampling duration tracking per bin
	sigDictCH0["TimeSinceEngineStart"] = timeSinceStart # Missing
	
	# 3. Print the corresponding variable's value
	printSignalValues(sigDictCH0, sigDictCH1)
	
	# 4. Select a mapping (bad / intermediate / good) (cold / hot start)
	# * Fault active part is omitted
	## A. New Concept
	### barometric (kpa): mbar = 10 x kPa
	### * Assuming T_SCR == EngCoolantTemp (THIS IS PROBABLY NOT CORRECT)
	if (sigDictCH0["TimeSinceEngineStart"] < 180 
		or sigDictCH0["AmbientAirTemp"] < -7 
		or sigDictCH0["BarometricPress"] * 10 < 750 
		or sigDictCH0["EngCoolantTemp"] < 180):
		print("Bad Mapping")
	elif (sigDictCH0["TimeSinceEngineStart"] >= 180 
		and sigDictCH0["AmbientAirTemp"] >= -7 
		and sigDictCH0["BarometricPress"] * 10 >= 750):
		if 180 <= sigDictCH0["EngCoolantTemp"] < 220:
			print("Intermediate Mapping")
		elif sigDictCH0["EngCoolantTemp"] >= 220:
			print("Good Mapping")
	## B. Old Concept
	# * Fault active part is omitted
	if (sigDictCH0["TimeSinceEngineStart"] >= 1800
		and sigDictCH0["AmbientAirTemp"] >= -7
		and sigDictCH0["BarometricPress"] * 10 >= 750):
		print("Old Concept Good Mapping")
	## C. PEMS Concept
	if (sigDictCH0["TimeSinceEngineStart"] >= 60
		and sigDictCH0["AmbientAirTemp"] >= -7 
		and sigDictCH0["BarometricPress"] * 10 >= 750):
		if 30 <= sigDictCH0["EngCoolantTemp"] < 70:
			print("PEMS - cold start part")
		elif sigDictCH0["EngCoolantTemp"] >= 70:
			print("PEMS - hot start part")
	
	# 5. Time delay
	time.sleep(1)



"""
	# <Old Version>
	# 1. Save signals' values from the target path signal dictionaries
	####### - can0 - #######
	ambientAirTemp = checkPath("Vehicle.AmbientAirTemperature")
	percentTorque = checkPath(
		"Vehicle.Drivetrain.InternalCombustionEngine.Engine.ActualEngPercentTorque")
	barometricPress = checkPath("Vehicle.OBD.BarometricPressure")
	airIntakeTemp = checkPath("Vehicle.OBD.IntakeTemp")
	coolantTemp = checkPath("Vehicle.OBD.CoolantTemperature")
	fuelRate = checkPath("Vehicle.OBD.FuelRate")
	percentLoadAtSpeed = checkPath(
		"Vehicle.OBD.EngPercentLoadAtCurrentSpeed")
	engSpeed = checkPath(
		"Vehicle.Drivetrain.InternalCombustionEngine.Engine.Speed")
	frictionPercentTorque = checkPath(
		"Vehicle.Drivetrain.InternalCombustionEngine.Engine.NominalFrictionPercentTorque")
	####### - can1 - #######
	intakeNOx = checkPath(
		"Vehicle.AfterTreatment.NOxLevel.NOxIntake1")
	outletNOx = checkPath(
		"Vehicle.AfterTreatment.NOxLevel.NOxOutlet1")
	frictionPercentTorqueVector = checkPath(
		"Vehicle.Drivetrain.InternalCombustionEngine.Engine.NominalFrictionPercentTorqueVector")

	# 2. Store newly retrieved data to the dictionary keys
	####### - can0 - #######
	sigDictCH0["AmbientAirTemp"] = ambientAirTemp
	sigDictCH0["ActualEngPercentTorque"] = percentTorque
	sigDictCH0["BarometricPress"] = barometricPress
	sigDictCH0["EngAirIntakeTemp"] = airIntakeTemp
	sigDictCH0["EngCoolantTemp"] = coolantTemp
	sigDictCH0["EngFuelRate"] = fuelRate
	sigDictCH0["EngPercentLoadAtCurrentSpeed"] = percentLoadAtSpeed
	sigDictCH0["EngSpeed"] = engSpeed
	sigDictCH0["NominalFrictionPercentTorque"] = frictionPercentTorque
	####### - can1 - #######
	sigDictCH1["Aftertreatment1IntakeNOx"] = intakeNOx
	sigDictCH1["Aftertreatment1OutletNOx"] = outletNOx
	sigDictCH1["NominalFrictionPercentTorque"
		] = frictionPercentTorqueVector
"""
