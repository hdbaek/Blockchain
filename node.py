# Simple blockchain node
# Original source modified by HD BAEK
# For the purpose of test, some functions are implemented differently from
# the original specifications.
# Usage : python node.py -i 127.0.0.1 -p 5000
# Usage : python node.py (by default)

import hashlib
import json
import requests
from time import time
from uuid import uuid4
from flask import Flask, jsonify, request
from urllib.parse import urlparse
from argparse import ArgumentParser
import optparse
import eth_keys, binascii
import requests

class Blockchain(object):
	def __init__(self):
		self.chain = []
		self.current_transactions = []
		self.myAddress = "0xBAe746299e7dEAF3dD05f085E305B3e4ba8CB7D3"
		
        # Creates the genesis block. Initial target is 0x0c03a30c
		self.new_block(previous_hash='000001', target=0x1f03a30c) #0x1e03a30c is more difficult
        # insert coinbase of genesis block
		self.new_transaction(
			sender = "0",
			recipient=self.myAddress,
			amount='50',
			script='This is coinbase of genesis block',
		)
		self.chain[-1]['transactions'] = self.current_transactions
		self.current_transactions = []
		
		# change with every 10 seconds
		self.point_time_interval = int(int(time())/10)
		# True if a block is mined in the above time interval
		self.is_mined_in_this_interval = True 
		
		self.nodes = set() # add(x), pop()
 
	def register_node(self, address):
		parsed_url = urlparse(address)
		self.nodes.add(parsed_url.netloc)
 
	def valid_chain(self, chain):
		"""
		Determine if a given bchain is valid
		:param chain: A bchain
		:return: True if valid, False if not
		"""
		last_block = chain[0]
		current_index = 1
		while current_index < len(chain):
			block = chain[current_index]
			print(f'{last_block}')
			print(f'{block}')
			print("\n----------\n")
            # Check that the hash of the block is correct
			if block['previous_hash'] != self.hash(last_block):
				return False
				
			# Check that the Proof of Work is correct
			if self.valid_target(block['previous_hash'], block['dateCreated'], block['nonce'], block['difficulty']) == False:
				return False
			
			last_block = block
			current_index += 1
 
		return True
 
	def new_block(self, target, previous_hash=None, nonce=None, miner=None, dateCreated=None):
		"""
		Creates a new Block and adds it to the chain
		:param target: <int> The target given by the Proof of Work algorithm
		:param previous_hash: (Optional) <str> Hash of the previous Block
		:return: <dict> New Block
		"""
		block = {
			'index': len(self.chain) + 1,
            'transactions': self.current_transactions,
            'difficulty': target,
            'previous_hash': previous_hash or self.hash(self.chain[-1]),
			'minedBy': miner,
			'nonce': nonce,
			'timestamp': time(), # for the 10 seconds interval
			'dateCreated': dateCreated,
		}		
		
		# Reset the current list of transactions
		self.current_transactions = []
		
		# Before insertion to a block, mark UTXO
		for tx in self.current_transactions:
			self.utxoMark(tx['utxoId'], tx['utxoIndex'])
			
		self.chain.append(block)			

		return block
	
	def new_transaction(self, sender, recipient, amount, utxoId=None, utxoIndex = None, signature=None, 
				pubKey=None, script=None):
		"""
		Adds a new transaction to the list of transactions
		:param sender: <str> Address of the Sender
		:param recipient: <str> Address of the Recipeint
		:param amount: <int> Amount
		:return: <int> The index of the Block that will hold this transaction
		"""
		# The format of serialized TX data is different from this. It is just for an example
		# Transaction ID(txId) is not included in the real Bitcoin system, it is for convenience.
		script = script or int(time()*10) # to make the coinbase txid differently
		tx_data = {sender, recipient, amount, utxoId, signature, pubKey, script}
		txId = hashlib.sha256(str(tx_data).encode('utf8')).hexdigest()
			
		# Inital the new TX is all UTXO for each recipient		
		isUtxo = 's'
		recipients = recipient.split(',')
		for i in range(len(recipients)):
			isUtxo = isUtxo + ',' + str(True)
		isUtxo = isUtxo[2:]
		
		self.current_transactions.append({
            'sender': sender,
            'recipient': recipient, # TXOUT
            'amount': amount, # TXOUT
			'senderPubkey':pubKey, # TXIN inscript
			'senderSignature':signature, # TXIN in script
			'utxoId':utxoId,  # TXIN : TX ID of UTXO
			'utxoIndex':utxoIndex, # TXIN : Index of TX ID ==> for above utxoId
			'txId':txId,  # TX ID for this TX
			'script':script, # TXIN, TXOUT
			'isUtxo':isUtxo, # for each "recipient" indicates if it is UTXO or not 
		})
		
		# In case of Coinbase, there is no utxoId referenced		
		if utxoId == None:
			return self.last_block['index'] + 1	
			
		# Make all isUtxo field of a TX Fase when referenced by utxoID + utxoIndex 
		# To prevent double spent, this may require
		self.utxoMark(utxoId, utxoIndex)
					
		return self.last_block['index'] + 1
		
	# Make all isUtxo field of a TX Fase when referenced by utxoID + utxoIndex 
	def utxoMark(self, utxoId, utxoIndex):
		utxoIds = utxoId.split(',')
		utxoIndexs = utxoIndex.split(',')
		for block in self.chain:
			transactions = block['transactions']
			for tx in transactions:				
				i = -1
				for utxoId in utxoIds:
					i = i + 1
					if tx['txId'] == utxoId: # found TX
						recipients = tx['recipient'].split(',')
						j = -1
						for recipient in recipients:
							j = j + 1
							if j == int(utxoIndexs[i]): # found Index
								isUtxoIds = tx['isUtxo'].split(',')
								isUtxoIds[j] = str(False) # set this is not UTXO
								# change to string and assign
								isUtxoS = 'S'
								for s in isUtxoIds:
									isUtxoS = isUtxoS + ',' + s
								tx['isUtxo'] = isUtxoS[2:]  # make in TX that this not UTXO
								break	
	
	@staticmethod
	def hash(block):
		"""
		Creates a SHA-256 hash of a Block
		:param block: <dict> Block
		:return: <str>
		 """
		block_string = json.dumps(block, sort_keys=True).encode()
		return hashlib.sha256(block_string).hexdigest()														
 
	@property
	def last_block(self):
		# Returns the last Block in the chain
		return self.chain[-1]

	def reTarget(self, last_target):
		"""
		BitCoin reTargeting rule :
		New Target = Old Target * (Acual Time of Last 2016 Blocks / 20160 minutes)
		Here, simply assumes that target value decrease by 0.1%  
		Then, for simplicity and testing purpose, it increased by 10% every time
		"""
		target = int(last_target - last_target * 0.001)
		return target

	@staticmethod
	def valid_target(blockDataHash, dateCreated, nonce, target):
		"""
		Valify if the mined block hash value satisfy the target
		In Bitcoin, blockDataHash should be the previous block header itself.
		Here, for the purpose of test, we use the previous block hash instead.
		Target means difficulty
		"""		
		coefficient = int(hex(target)[-6:], 16)
		exponent = int(hex(target)[:-6], 16)
		targetValue =  coefficient * (2 ** (8*(exponent-3)))
		t = blockDataHash + "|" + str(dateCreated) + "|" + nonce
		minedBlockHash = hashlib.sha256(t.encode("utf8")).hexdigest()
		
		if (int(minedBlockHash,16) < targetValue):
			return True
		else:
			return False

	def resolve_conflicts(self):
		"""
	   This is our consensus algorithm, it resolves conflicts
	   by replacing our chain with the longest one in the network.
	   :return: True if our chain was replaced, False if not
	   """
		neighbours = self.nodes
		new_chain = None

		# We're only looking for chains longer than ours
		max_length = len(self.chain)

		# Grab and verify the chains from all the nodes in our network
		for node in neighbours:
			response = requests.get(f'http://{node}/chain')

			if response.status_code == 200:
				length = response.json()['length']
				chain = response.json()['chain']

				# Check if the length is longer and the chain is valid
				if length > max_length and self.valid_chain(chain):
					max_length = length
					new_chain = chain

		# Replace our chain if we've discovered a new, valid chain, longer then ours
		if new_chain:
			self.chain = new_chain
			return True

		return False

# Instantiate our Node
app = Flask(__name__)
# Generate a globally unique address for this node
node_indentifier = str(uuid4()).replace('-', '')
# Instantiate the Blockchain
bchain = Blockchain()

@app.route('/mining/get-mining-job/<address>', methods=['GET'])
def mine(address):
	# check if 10 seconds have passed and no mining is done
	if int(bchain.chain[-1]['timestamp']/10) == int(time()/10):
		return jsonify( { 'msg' : 'waiting for interval' } ), 400

	last_block = bchain.last_block
	last_target = last_block['difficulty']
	target = bchain.reTarget(last_target)

	previous_hash = bchain.hash(last_block)
	response = {
		'index': len(bchain.chain) + 1,
		'difficulty': target,
		'blockDataHash': previous_hash,
		'miner': address
	}
	return jsonify(response), 200

@app.route('/mining/submit-mined-block/<address>', methods=['POST'])
def minedBy(address):	
	# Validate the miner'data and POW
	values = request.get_json()
	if bchain.chain[-1]['previous_hash'] == values['blockDataHash']:
		return jsonify( { 'errorMsg' : 'mining failed' } ), 400
		
	required = ['blockDataHash', 'dateCreated','nonce','blockHash']
	if not all(k in values for k in required):
		return jsonify({ 'errorMsg': 'Missing values' }), 400

	errorMsg = { "errorMsg":"Invalid Proof of Work", "miner":address }
	last_block = bchain.last_block
	last_target = last_block['difficulty']
	target = bchain.reTarget(last_target)
	if(bchain.valid_target(bchain.hash(last_block), values['dateCreated'], values['nonce'], target) == False):
		return jsonify(errorMsg), 401

	# We must give a reward for finding the target to the address of miner.
	# The sender is "0" to signify that this miner has mine a new coin.
	bchain.new_transaction(
		sender="0",
		recipient=address,
		amount='12.5',
	)

	# Forge the new Block by adding it to the chain
	block = bchain.new_block(target=target, nonce=values['nonce'], miner=address, dateCreated=values['dateCreated'])
					
	index = block['index']
	response = {
		'message': f'new Block will be added : index = {index}'
	}
	return jsonify(response), 200

# Inspect and find a tx in the buffer which are not mined
def explorer_TX(txId):
	transactions = bchain.current_transactions
	for tx in transactions:		
		if tx['txId'] == txId:			
			response = {
				'status':'===  In Progressing ====',
				'txID':tx['txId'],
				'sender':tx['sender'],
				'recipinet':tx['recipient'],
				'amount':tx['amount'],
				'utxoId':tx['utxoId'],
				'utxoIndex':tx['utxoIndex'],
			}
			return True, jsonify(response)
	return False, None

# Find all the UTXOs of a given address
# When a TX receive from the wallet, even if is not mined, to prevent the double spent, the referenced
# TX in TX INPUT regarded as used  
def find_UTXO(address):
	response = []
	balance = 0
	for block in bchain.chain:
		transactions = block['transactions']
		for tx in transactions:	
			recipients = tx['recipient'].split(',')
			isUtxos = tx['isUtxo'].split(',')
			i = -1
			for recipient in recipients:
				i = i + 1
				if (recipient == address) and (isUtxos[i] == str(True)):
					amounts = tx['amount'].split(',')
					balance = balance + float(amounts[i])
					response.append({				
						'value':amounts[i],
						'txId':tx['txId'],
						'txIdIndex':str(i),	
					})
	return response, balance
	
@app.route('/explorer/<keyword>', methods=['GET'])
def explorer(keyword):
	if keyword[:4] == 'utxo': # find all UTXOs
		address = keyword[5:]
		r1, r2 = find_UTXO(address)
		return jsonify(r1), 200
	elif keyword[:5] == 'block':
		blockId = keyword[6:]
		if len(blockId) == 0:
			return jsonify({ 'errorMsg':'null'}), 400
		if blockId == 'size':
			response = { 'Block size':len(bchain.chain) }
			return jsonify(response), 200
		try:
			if (int(blockId) > len(bchain.chain)) or (int(blockId) <= 0): 
				return jsonify( { 'errorMsg':'too big or invalid index'} ), 400 
		except ValueError:
			print("error in explorer:"+ValueError)
			
		chain = bchain.chain[int(blockId)-1]
		response = {
			'index':chain['index'],
			'transactions':chain['transactions'],
		}
		return jsonify(response), 200 
	elif keyword[:2] == 'tx':
		txId = keyword[3:]		
		r1, r2 = explorer_TX(txId)
		if r1 == True:
			return r2, 200
		size = 0
		for block in bchain.chain:
			transactions = block['transactions']
			for tx in transactions:		
				size = size + 1
				if tx['txId'] == txId:			
					response = {				
						'txId':tx['txId'],
						'sender':tx['sender'],
						'recipinet':tx['recipient'],
						'amount':tx['amount'],
						'utxoId':tx['utxoId'],
						'utxoIndex':tx['utxoIndex'],
					}
					return jsonify(response), 200	
					
		if txId == 'size':
				return jsonify( { 'TX size':size} ), 200
		return jsonify({ "errorMsg":"not found"}), 400

@app.route('/transactions/new', methods=['POST'])
def new_transaction():
	values = request.get_json()
 
	# Check that the required fields are in the POST'ed data.
	required = ['sender', 'recipient', 'amount']
	if not all(k in values for k in required):
		return 'Missing values', 400
 
	"""
	# The format of serialized TX data is different from this. It is just for an example 
	tx_data = { values['sender'], values['recipient'], values['amount'], values['utxoId'],
		values['senderSignature'], values['senderPubkey']}
	# Transaction ID(txId) is not included in the real Bitcoin system, it is for convenience.
	txId = hashlib.sha256(str(tx_data).encode('utf8')).hexdigest()
	"""
	# verify the TX data received
	if valid_transaction(values) == False:
		return jsonify({ "errorMsg" : "TX validation failed" }), 400
		
	# Create a new transaction 
	# recipient, amount, utxoId, signature can be multiple
	index = bchain.new_transaction(values['sender'], values['recipient'], values['amount'], 
		utxoId=values['utxoId'], utxoIndex=values['utxoIndex'], signature=values['senderSignature'])
	
	response = {
		'sender':values['sender'],
		'recipient':values['recipient'],
		'amount':values['amount'],
		'utxoId':values['utxoId'], 
		'txId':bchain.current_transactions[-1]['txId'],
	}
	return jsonify(response), 201
 
def valid_transaction(values):
	# Verify the signatures for all UTXOs match to the recipient's publicKey and address 
	# Below code does not work. Why ? Sign using JavaScript ethers and verify using python. 
	"""
	signature = eth_keys.keys.Signature(binascii.unhexlify(values['senderSignature'][2:]))
	signerPubKey = signature.recover_public_key_from_msg(values['utxoId'])
	signerAddress = signerPubKey.to_checksum_address()
	if signerAddress == values['sender'][2:]:
		print("TX valid success ======");
		return True
	else:
		print("TX valid failed =====");
		return False
	"""
	# Verify UTXOs used and sum of them are bigger than the amount to sender
	# When receiving one TX, all its UTXOs in the block is marked as unusable
	# But the remained amount after use which is destined to the sender can be not be used util it is mined
	sum = 0
	v_string = values['amount'].split(',')
	for ss in v_string:
		sum = sum + float(ss)
	r1, r2 = find_UTXO(values['sender'])
	if r2 < sum:
		return False

	return True
	
@app.route('/chain', methods=['GET'])
def full_chain():
	response = {
		'chain': bchain.chain,
		'length': len(bchain.chain),
	}
	return jsonify(response), 200
 
 
@app.route('/nodes/register', methods=['POST'])
def register_nodes():
	values = request.get_json()
	nodes = values.get('nodes')
	if nodes is None:
		return "Error: Please supply a valid list of nodes", 400
 
	bchain.register_node(nodes)
	
	response = {
		'message': 'New nodes have been added.',
		'total_nodes': list(bchain.nodes),
	}
	return jsonify(response), 201
 
 
@app.route('/nodes/resolve', methods=['GET'])
def consensus():
	replaced = bchain.resolve_conflicts()
 
	if replaced:
		response = {
			'message': 'Our chain was replaced',
			'new_chain': bchain.chain
		}
	else:
		response = {
			'message': 'Our chain is authoritative',
			'chain': bchain.chain
		}
	return jsonify(response), 200

def register(url, myIp):
    data = { 
	    'message': 'Good morning',
	    'nodes':'http://'+ myIp, 
	}
    resp = requests.post(url + "/nodes/register", json=data)	
    print("response=", resp.text)
 
if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=5000, type=int, help='port to listen on')
    parser.add_argument('-i', '--ipAddr', default='127.0.0.1', type=str, help='host ip address')
    parser.add_argument('-r', '--remote', default=None, type=str, help='url for neighbor node')
    args = parser.parse_args()
    port = args.port
    hostip= args.ipAddr
    if args.remote != None: # for the interworking with more than two nodes
        register('http://' + args.remote, hostip+':'+ str(port))
        bchain.register_node('http://' + args.remote)
        bchain.myAddress = "0x3D9A7431B6ADB5E1E6e9136a97F513e950f34268"
    app.run(host=hostip, port=port)