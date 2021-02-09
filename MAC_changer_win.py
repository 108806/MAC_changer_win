import os

print(os.getcwd())

import re
import subprocess
import sys

if sys.platform != 'win32':
	print('This platform is not supported nor targeted in this version')
	sys.exit(1)
import winreg
from functools import lru_cache

# 12 HEX vals per MAC addr:
desired_macs = ['DEADBEEFBABE', '000108806000']

mac_addresses = []

# REGEX for matchig any MAC addr:
mac_add_re =  re.compile(r"([A-Fa-f0-9]{2}[:-]){5}([A-Fa-f0-9]{2})")

# REGEX for transport names:
transportName = re.compile("({.+})")

# Regex to pick out the adapter index:
adapterIndex = re.compile("([0-9]+)")

# Get MAC addresses from there:
getmac_out = subprocess.run("getmac",
	capture_output=True).stdout.decode().split('\n')


def theCore(output:list=getmac_out):


	for MAC in output:
		macFind = mac_add_re.search(MAC)
		transportFind = transportName.search(MAC)

		if not macFind or not transportFind:
			continue
		mac_addresses.append((macFind.group(0), transportFind.group(0)))


	# Simple menu:

	_DEVICES = (F" {index} - MAC : {item[0]} - Transport Name: {item[1]}"
		for index, item in enumerate(mac_addresses))
	_NEW_MAC = (F" {index} - MAC : {item}"
		for index, item in enumerate(desired_macs))

	# Get fist opt:
	print(*_DEVICES,sep='\n')

	dev_option = input('Select the MAC addr to be changed: ')

	while not dev_option:
		dev_option = input('No input detected. Try again.')

	while dev_option not in tuple(str(x) for x in range(len(mac_addresses))):
		print(*_DEVICES)
		dev_option = input('Select the MAC addr to be changed: ')

	try:
		dev_choice = mac_addresses[int(dev_option.strip())][1]
		print(f'[INFO] Selected {dev_choice}')
	except IndexError:
		print(F"""
		Wrong choice of {dev_option}.
		Choose in range 0 - {len(mac_addresses)-1}
		""")


	# Get second opt:
	print(*_NEW_MAC, sep='\n')
	mac_option = input('Select your desired MAC addr:')

	while not mac_option:
		mac_option = input('No input detected. Try again.')

	while mac_option not in tuple(str(x) for x in range(len((desired_macs)))):
		print(*_NEW_MAC, sep='\n')
		mac_option = input('Select your desired MAC addr from list:')

	try:
		mac_choice = desired_macs[int(mac_option.strip())]
		print(f'[INFO] Selected {mac_choice}')

	except Exception as e:
		print(e)


	# Get confirmation:
	print(F"""
		You are about to change your mac to : {mac_choice}
		On the following device : {dev_choice}
		""")

	confirmation = lambda : input("Is this OK? Choose : yes / no\n")
	while confirmation().lower().strip() not in ('yes', 'y'):
		confirmation()
	print('Choices are confirmed.')

	# This is the exact place where every win reg holds dev info(!):
	controller_key_part ="""
	SYSTEM\\ControlSet001\\Control\\Class\\{4d36e972-e325-11ce-bfc1-08002be10318}\
	""".strip() # Strip kills the trailing newLine, a great place for a very annoying bug.

	# None means we connect to local machine's registry:
	with winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE) as hkey:

		@lru_cache(maxsize=None)
		def keyGen():
			"""
			Generates the suffixes for the folder names.
			Returns : list of strings like \\0013
			"""
			func = lambda i : "\\0000"[:-len(i)] + i
			arr = (str(j) for j in range(0,21))
			return tuple(map(func, arr))

		keys = keyGen()

		def keyIter():
			for key_folder in keys:
				print('[INFO] : Enumerating the folder - ', key_folder)
				try:
					with winreg.OpenKey(hkey, controller_key_part + key_folder,
						0, winreg.KEY_ALL_ACCESS) as regkey:
						# Now looking for the NetCFGInstanceId:
						try:
							count = 0
							while True:
								name, value, _ = winreg.EnumValue(regkey, count)
								name = name.strip()
								count += 1
								if name == 'NetCfgInstanceId':
									print('[INFO] Got name : ', name, " VS ", 'NetCfgInstanceId')
									print('[INFO] Got value ' + value + ' VS ' + dev_choice)

								if name == "NetCfgInstanceId" and value == dev_choice:
									print('[INFO] : Got matching ID - ', dev_choice)
									new_mac_addr = mac_choice
									winreg.SetValueEx(regkey, "NetworkAddress",
									0, winreg.REG_SZ, new_mac_addr)
									print("[INFO] Matched the target Transport Number")
									return

						except WindowsError as e:
							pass

				except Exception as e:
					print(e, controller_key_part + key_folder)
		keyIter()

		# Option to disablethe Wireless devices:
		run_disabler = input(
			"Do you want to disable and re-enable your wireless device(s)? Y / N\n")
		if run_disabler.lower() == 'y':
			run_last_part = True
		else:
			run_last_part = False


		while run_last_part:
			net_adapters = subprocess.run(['wmic', 'nic', 'get', 'name, index'],
				capture_output=True).stdout.decode('utf-8',
				errors='ignore').split('\r\r\n')
			for adapter in net_adapters:
				print(adapter)
				adapter_index_find = adapterIndex.search(adapter.strip())

				if adapter_index_find and 'Wireless' in adapter:
					disable = subprocess.run(['wmic, path, win32_networkadapter',
						'where', f'index={adapter_index_find.group(0)}',
						'call', 'disable'],
						capture_output=True)

					if(disable.returncode == 0):
						print(f"Disabled {adapter.strip()}")

						enable = subprocess.run([
							"wmic", "path", f"win32_networkadapter",
							"where", f"index={adapter_index_find.group(0)}",
							"call", "enable"],
							capture_output=True)

						if (enable.returncode == 0):
							print(f"Enabled {adapter.lstrip()}")

			getmac_output = subprocess.run("getmac",
				capture_output=True).stdout.decode()

			# We recreate the Mac Address as ot shows up in getmac XX-XX-XX-XX-XX-XX
			# format from the 12 character string we have.
			# We split the string into strings of length 2 using list comprehensions and then.
			# We use "-".join(list) to recreate the address
			mac_add = "-".join([(mac_choice[i:i+2]) for
				i in range(0, len(mac_choice), 2)])

			if mac_add in getmac_output:
				print("Mac Address Success")
				break
			else:
				print("[WARNING] MAC change failed.")
				sys.exit(1)




if __name__ == '__main__':
	theCore()
