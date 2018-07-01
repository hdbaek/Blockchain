
# Blockchain Miner entity
# Written by H.D. BAEK 
# Usage : python miner.py -a 0xD229c1d39E436a5f43AeDEA521F14731885B7d6d -u http://localhost:5000

# imports the standard JSON parser, the REST library, libraries for cryptography and others
import json
import requests
import time, datetime
import hashlib
import sys	
import optparse

# REST GET command to the blockchain network
def miner_get(url, data=None):
	response = requests.get(url, data=data, headers={'content-type':'application/json', 'accept':'application/json'})	
	return response

# main function : miner start from here
# main() gets two options. first one is the address of a miner and second is node's URL
# Usage : python miner.py -a 0xD229c1d39E436a5f43AeDEA521F14731885B7d6d -u http://localhost:5000
def main():
	parser = optparse.OptionParser()
	parser.add_option('-a', '--address', action="store", dest="address", help="miner address", default="0xD229c1d39E436a5f43AeDEA521F14731885B7d6d")
	parser.add_option('-u', '--url', action="store", dest="url", help="url of a node", default="http://localhost:5000")
	options, args = parser.parse_args()
	miner_address = options.address
	node_url = options.url + "/"
	print("miner_address: ", miner_address, "url of a node: ", node_url)
	
	# for testing : node_url = "http://stormy-everglades-34766.herokuapp.com:80"
	# miners continue to try to mine
	# request a block be mined to the networks(Nodes)
	# then try to find a hashing code and nonce value to meet with the difficulty 
	# indicates if the previous try of mining was successed 
	while True:		
		# Request and wait a response from the networks		
		print("::::: First Stage : Request a candidate mining block to Node")		
		resp = miner_get(node_url + "mining/get-mining-job/" + miner_address)		
		print("====> First Stage : Response received from Node: ", resp)
		print(resp.text)
		if resp.status_code != 200:
			continue
			
		resp_text = json.loads(resp.text)
	
		# handle the received text
		# blockDataHash = resp_text['chain'][0]['blockDataHash']
		blockDataHash = resp_text['blockDataHash']
		
		# calculate UTC time like "2018-02-11T20:31:32.397Z"
		dateCreated = createCurrentTime()
		
		# difficulty = resp_text['chain'][0]['difficulty']
		#difficulty = resp_text['difficulty']
		#index = resp_text['index']
		
		#nonce = 1  # initially set to 1
		#zero_string = '0000000000000000000000000000000000000000'  # maximum 40 bits for this program
		#current = time.time() # get the current time in second	
		
		# Miner requests a candidate block to Nodes by this interval time 
		interval = 0.1; 		
		while True:
			nonce, minedBlockHash = findminedDataHash(resp_text, dateCreated, interval, node_url, miner_address)
			if nonce != 0: 
				break
			else: # trying to find the hash again after changing the timestamp
				dateCreated = createCurrentTime()
				continue
				
		if minedBlockHash == 0: # another miner found the hash. stop mining
			continue
				
		# In the Bitcoin system, if the mining node failed to find the 'minedBlockHash' within 
		# the four-byte nonce value, the node calls the above 'findminedDataHash' again with new 'dateCreated'
		
		# After finding a hashcode, now submit the mined block by POST
		# Data for POST
		data = { 
		    "blockDataHash": blockDataHash, 
			"dateCreated": dateCreated, 
			"nonce": str(nonce), 
			"blockHash": minedBlockHash 
		}
		
		print("")
		print("::::: Second Stage : Post the mining result to Node :", data)
		resp = requests.post(node_url + "mining/submit-mined-block/" + miner_address, json=data)
		try :
			resp_text = json.loads(resp.text)
		except ValueError:
			print('{}'.format(resp.text))
		print("====> Second Stage : Response received with return code: ", resp.status_code)
		if (resp.status_code == 200):
			print("===================================================")
			print("")
			print("               MINING SUCCESS !!!")
			print("")
			print("===================================================")
		else :  # mining failed - another miner found the hash avlue in advance
			print("Error message: ", resp_text['errorMsg'])
		
		print("")

# In the while loop, calculates some special hashing value as incrementing the nonce value 
# until satisfied value is found
def findminedDataHash(blockInfo, dateCreated, interval, node_url, miner_address):
	# four byte nonce value initially set to 1
	nonce = 1 
	
	# get the current time in second
	current = time.time() 	
	
	# The hash value of previous block header
	blockDataHash = blockInfo['blockDataHash']	
	
	# Here, difficulty means the number of zero's in hex code 
	# So number of first zero bits in the hash is difficulty * 4
	difficulty = blockInfo['difficulty'] 
	
	# Index is to distingish a block. There is no index in the real block chain system
	index = blockInfo['index']  
	# target is caculated from difficulty
	target = getTargetValue(difficulty)
	
	# Miner requests a candidate block to Nodes by this interval time 
	# Because the dificulty is too easy for this program, use this short value
	while True:
		# Mined block hash value calculated by sha256 of below three data
		t = blockDataHash + "|" + str(dateCreated) + "|" + str(nonce)
		minedBlockHash = hashlib.sha256(t.encode("utf8")).hexdigest()
		
		# Check if the value meet the target required
		if int(minedBlockHash, 16) < target:
			return nonce, minedBlockHash
				
		# Before starting the next loop, check if one interval has passed after the initial start of current mining
		# if it does, request another candidate mining block to check if current block is mined, if it does
		# the miner stops the current mining process and request another one
		# This module can be implemented by a thread process to continue current mining process without stop
		if (time.time()-current) > interval :  
			print("**************** ", interval, "ONE INTERVAL PASSED ************************")
			resp = miner_get(node_url + "mining/get-mining-job/" + miner_address)
			resp_text = json.loads(resp.text)
			if resp_text['index'] != index : # failed in mining -- another miner did
				print("************ FAILD IN MINING (block = {index}) **************")
				return nonce, 0
			
		if nonce == 0xffffffff: # exhaust all nonce values
			return 0, 0
			
		nonce = nonce + 1  # increment
		current = time.time()	
		
# In the bitcoin system, difficulty(target) is 4 byte long
# First one byte is exponent(E) and last 3 bytes is coefficient. 
# Target = coefficient * (2 ** (8*(E-3)))			
def getTargetValue(difficulty):
	coefficient = int(hex(difficulty)[-6:], 16)
	exponent = int(hex(difficulty)[:-6], 16)
	print("*** target value = ", hex(coefficient * (2 ** (8*(exponent-3)))))
	return coefficient * (2 ** (8*(exponent-3)))

def createCurrentTime():
	# calculate UTC time like "2018-02-11T20:31:32.397Z"
	timeNow = datetime.datetime.now()
	timeNow = timeNow + datetime.timedelta(hours=9)
	return timeNow.strftime('%Y-%m-%dT%H:%M:%SZ')
	
if __name__ == "__main__":
    main()
	
