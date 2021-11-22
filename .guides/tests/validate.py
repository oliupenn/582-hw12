from web3 import Web3
import sys
from os import path
import requests
import random
from vyper import compile_code, compile_codes

w3 = Web3(Web3.EthereumTesterProvider())

# set pre-funded account as sender
sender_address = w3.eth.accounts[0]
userA = w3.eth.accounts[1]
userB = w3.eth.accounts[2]
w3.eth.default_account = sender_address

def createERC20(name,symbol,decimals,supply,minter_address):
	ERC20_file="ERC20.vy"
	if not path.exists(ERC20_file):
		url = 'https://raw.githubusercontent.com/vyperlang/vyper/master/examples/tokens/ERC20.vy'
		r = requests.get(url)
		with open(ERC20_file, 'wb') as f:
			f.write(r.content)
			
	with open(ERC20_file,"r") as f:
		contract_source=f.read()

	contract_dict = compile_codes(contract_sources={ERC20_file:contract_source},output_formats=["bytecode","abi"])
	ERC20_contract = w3.eth.contract(abi=contract_dict[ERC20_file]['abi'], bytecode=contract_dict[ERC20_file]['bytecode'])

	# Submit the transaction that deploys the contract
	tx_hash = ERC20_contract.constructor(name,symbol,decimals,supply).transact({"from":minter_address})

	# Wait for the transaction to be mined, and get the transaction receipt
	tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

	ERC20_contract = w3.eth.contract(abi=contract_dict[ERC20_file]['abi'], address=tx_receipt.contractAddress )
	return ERC20_contract

#Create some new ERC20 tokens that we can work with
num_tokens = 10
tokens = [createERC20(f"token{hex(i)[2:]}",f"{hex(i)[2:]}{hex(i)[2:]}{hex(i)[2:]}",0,10**7,sender_address ) for i in range(num_tokens) ]

for i in range(num_tokens):
	tokens[i].functions.mint(userA,10**6).transact({"from":sender_address}) 
	tokens[i].functions.mint(userB,50**6).transact({"from":sender_address}) 

ERC20_ABI=tokens[0].abi #Get the ABI (Application Binary Interface)

def createAMM(student_repo_path):
	contract_filename= student_repo_path + "/AMM.vy"
	with open(contract_filename,"r") as f:
		contract_source=f.read()
	contract_dict = compile_codes(contract_sources={contract_filename:contract_source},output_formats=["bytecode","abi"])
	AMM = w3.eth.contract(abi=contract_dict[contract_filename]['abi'], bytecode=contract_dict[contract_filename]['bytecode'])

	# Submit the transaction that deploys the contract
	tx_hash = AMM.constructor().transact()

	# Wait for the transaction to be mined, and get the transaction receipt
	tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

	AMM = w3.eth.contract(abi=contract_dict[contract_filename]['abi'], address=tx_receipt.contractAddress )
	return AMM

def getContractState(AMM):
	state = {}
	state['tokenAQty'] = AMM.functions.tokenAQty().call()
	state['tokenBQty'] = AMM.functions.tokenBQty().call()
	state['tokenAAddr'] = AMM.functions.get_token_address(0).call()
	state['tokenBAddr'] = AMM.functions.get_token_address(1).call()
	state['invariant'] = AMM.functions.invariant().call()
	return state

def getUserState(AMM,addr):
	state = {}
	#tokenA = AMM.functions.tokenA().call()
	#tokenB = AMM.functions.tokenB().call()
	tokenA = w3.eth.contract(address=AMM.functions.get_token_address(0).call(),abi=ERC20_ABI)
	tokenB = w3.eth.contract(address=AMM.functions.get_token_address(1).call(),abi=ERC20_ABI)
	state['tokenAQty'] = tokenA.functions.balanceOf(addr).call()
	state['tokenBQty'] = tokenB.functions.balanceOf(addr).call()
	return state


def checkBalance(AMM,token):
	"""
	Takes two arguments, the AMM contract and an ERC20 contract "token"

	The AMM tracks the balance of tokens in its internal variables
	This function checks that the balance recorded in the ERC20 contract 
	matches the balance recorded in the AMM contract
	"""
	token_balance = token.functions.balanceOf(AMM.address).call()
	AMM_balance = 0
	if not token.address in [AMM.functions.tokenA().address,AMM.functions.tokenB().address]:
		print( f"Error: checkBalance called with invalid token" )
		return 0

	if AMM.functions.tokenA().address == token.address:
		AMM_balance = AMM.functions.tokenAQty().call()
	if AMM.functions.tokenB().address == token.address:
		AMM_balance = AMM.functions.tokenBQty().call()
	return token_balance == AMM_balance

def check_LP(AMM):
	"""
	The AMM contract must provide a "provideLiquidity" function
	This tests whether the providerLiquidity functions as it should
	"""

	tokenA_deposit = random.randint(50000,1000000)
	tokenB_deposit = random.randint(50000,1000000)
	i = random.randint(0,num_tokens-1)
	j = (i + random.randint(1,num_tokens-1))%num_tokens
	assert i != j
	tokenA = tokens[i]
	tokenB = tokens[j]

	tokenA.functions.approve(AMM.address,tokenA_deposit).transact({"from":sender_address})
	tokenB.functions.approve(AMM.address,tokenB_deposit).transact({"from":sender_address})
	AMM.functions.provideLiquidity(tokenA.address,tokenB.address,tokenA_deposit,tokenB_deposit).transact({"from":sender_address})
	invariant = tokenA_deposit * tokenB_deposit

	score = 0
	if AMM.functions.tokenAQty().call() == tokenA_deposit:
		print( "Success: tokenA deposited successfully" )
		score += 1
	else:
		print( f"Error: LP deposited {tokenA_deposit} of token {tokens[i].functions.symbol().call()} into contract at address {AMM.address} but the contract only received {AMM.functions.tokenAQty().call()}" )

	if AMM.functions.tokenBQty().call() == tokenB_deposit:
		print( "Success: tokenB deposited successfully" )
		score += 1
	else:
		print( f"Error: LP deposited {tokenB_amount} of token {tokens[i].functions.symbol().call()} into contract at address {BMM.address} but the contract only received {BMM.functions.tokenBQty().call()}" )

	if AMM.functions.owner().call() == sender_address:
		print("Success: provideLiquidity correctly set owner")
		score += 1
	else:
		print( f"Error: contract owner = { AMM.functions.owner().call() }, should be {sender_address}" )

	if AMM.functions.invariant().call() == tokenA_deposit*tokenB_deposit:
		print( "Success: provideLiquidity correctly set invariant" )
		score += 1
	else:
		print( f"Error: contract invariant = {AMM.functions.invariant().call()}, should be {tokenA_deposit*tokenB_deposit}" )

	return score

def check_trade(AMM,userA):
	"""
	Check whether the AMM correctly processes a trade from userA
	"""
	#Testing trading token A
	initial_contract_state = getContractState(AMM) 
	initial_user_balances = getUserState(AMM,userA)

	tokenA = w3.eth.contract(address=AMM.functions.get_token_address(0).call(),abi=ERC20_ABI)
	tokenB = w3.eth.contract(address=AMM.functions.get_token_address(1).call(),abi=ERC20_ABI)

	tradeA_amount = random.randint(1000,10000)
	tokenA.functions.approve(AMM.address,tradeA_amount).transact({"from":userA})
	AMM.functions.tradeTokens(tokenA.address,tradeA_amount).transact({"from":userA})

	final_contract_state = getContractState(AMM) 
	final_user_balances = getUserState(AMM,userA)

	score = 0
	if initial_contract_state['invariant'] == final_contract_state['invariant']:
		print("Success: invariant maintained after trade" )
		score += 1
	else:
		print( f"Error: invariant changed!" )

	if final_user_balances['tokenAQty'] + tradeA_amount == initial_user_balances['tokenAQty']:
		print( "Success: contract successfully withdrew tokenA from trader" )
		score += 1
	else:
		print( f"Error: contract failed to withdraw tokens from trader" )

	if final_contract_state['tokenAQty'] - tradeA_amount == initial_contract_state['tokenAQty']:
		print( "Success: contract successfully received tokenA" )
		score += 1
	else:
		print( f"Error: contract failed to receive tokens from trader" )
		print( f"Contract received {final_contract_state['tokenAQty'] - initial_contract_state['tokenAQty']}, but user sent {tradeA_amount}" )

	user_return = final_user_balances['tokenBQty'] - initial_user_balances['tokenBQty']
	min_return = initial_contract_state['tokenBQty'] - initial_contract_state['invariant']//(initial_contract_state['tokenAQty']+tradeA_amount)
	max_return = initial_contract_state['tokenBQty'] - initial_contract_state['invariant']//(initial_contract_state['tokenAQty']+tradeA_amount)
	if user_return < min_return:
		print( f"Error: user expected at least {min_return} but received {user_return}" )
	if user_return > max_return:
		print( f"Error: user expected at most {max_return} but received {user_return}" )

	#Testing trading token B
	initial_contract_state = getContractState(AMM) 
	initial_user_balances = getUserState(AMM,userA)

	tradeB_amount = random.randint(1000,10000)
	tokenB.functions.approve(AMM.address,tradeB_amount).transact({"from":userA})
	tx_hash = AMM.functions.tradeTokens(tokenB.address,tradeB_amount).transact({"from":userA})
	tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

	final_contract_state = getContractState(AMM) 
	final_user_balances = getUserState(AMM,userA)

	if initial_contract_state['invariant'] == final_contract_state['invariant']:
		print("Success: invariant maintained after trading tokenB" )
		score += 1
	else:
		print( f"Error: invariant changed!" )

	if final_user_balances['tokenBQty'] + tradeB_amount == initial_user_balances['tokenBQty']:
		print( "Success: contract successfully withdrew tokenB from trader" )
		score += 1
	else:
		print( f"Error: contract failed to withdraw tokens from trader" )

	if final_contract_state['tokenBQty'] - tradeB_amount == initial_contract_state['tokenBQty']:
		print( "Success: contract successfully received tokenB" )
		score += 1
	else:
		print( f"Error: contract failed to receive tokens from trader" )
		print( f"Contract received {final_contract_state['tokenBQty'] - initial_contract_state['tokenBQty']}, but user sent {tradeB_amount}" )

	user_return = final_user_balances['tokenAQty'] - initial_user_balances['tokenAQty']
	min_return = initial_contract_state['tokenAQty'] - initial_contract_state['invariant']//(initial_contract_state['tokenBQty']+tradeB_amount)
	max_return = initial_contract_state['tokenAQty'] - initial_contract_state['invariant']//(initial_contract_state['tokenBQty']+tradeB_amount)
	if user_return < min_return:
		print( f"Error: user expected at least {min_return} but received {user_return}" )
	if user_return > max_return:
		print( f"Error: user expected at most {max_return} but received {user_return}" )

	return score

def check_withdraw(AMM):
	"""
	Check whether the withdraw function of the AMM works properly
	"""
	initial_contract_state = getContractState(AMM) 
	initial_user_balances = getUserState(AMM,userA)

	tokenA = w3.eth.contract(address=AMM.functions.get_token_address(0).call(),abi=ERC20_ABI)
	tokenB = w3.eth.contract(address=AMM.functions.get_token_address(1).call(),abi=ERC20_ABI)
	
	score = 0
	try:  
		tx_hash = AMM.functions.ownerWithdraw().transact({'from': userA} )
		tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
	except Exception as e:
		print( f"Success: Contract prevented withdrawal from unauthorized user" )
		score += 1 
	
	final_contract_state = getContractState(AMM) 
	final_user_balances = getUserState(AMM,userA)

	if initial_contract_state['tokenAQty'] != final_contract_state['tokenAQty'] or initial_contract_state['tokenBQty'] != final_contract_state['tokenBQty']:
		print( f"Error: contract allowed a withdrawal from an invalid user" )
	else:
		score += 1 

	initial_contract_state = getContractState(AMM) 
	initial_user_balances = getUserState(AMM,sender_address)

	try:  
		tx_hash = AMM.functions.ownerWithdraw().transact({'from': sender_address})
		tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
		score += 1	
	except Exception as e:
		print( "Error: withdraw from owner failed" )
		print( f"Sender address = {sender_address}" )
		print( f"Contract owner = {AMM.functions.owner().call()}" )

	#Can't call getUserState if withdraw self destructs AMM
	#final_user_balances = getUserState(AMM,sender_address)
	final_user_balances = {}
	final_user_balances['tokenAQty'] = tokenA.functions.balanceOf(sender_address).call()
	final_user_balances['tokenBQty'] = tokenB.functions.balanceOf(sender_address).call()

	if final_user_balances['tokenAQty'] != initial_user_balances['tokenAQty'] + initial_contract_state['tokenAQty']:
		print( f"Error: contract failed to withdraw token A" )
		print( f"initial contract balance A = {initial_contract_state['tokenAQty']}" )
		print( f"initial user balance A = {initial_user_balances['tokenAQty']}" )
		print( f"sum = {initial_user_balances['tokenAQty'] + initial_contract_state['tokenAQty']}" )
		print( f"final user balance A = {final_user_balances['tokenAQty']}" )
	else:
		print( f"Success: withdraw of token A succeeded" )
		score += 1	
	if final_user_balances['tokenBQty'] != initial_user_balances['tokenBQty'] + initial_contract_state['tokenBQty']:
		print( f"Error: contract failed to withdraw token B" )
		print( f"initial contract balance B = {initial_contract_state['tokenBQty']}" )
		print( f"initial user balance B = {initial_user_balances['tokenBQty']}" )
		print( f"sum = {initial_user_balances['tokenBQty'] + initial_contract_state['tokenBQty']}" )
		print( f"final user balance B = {final_user_balances['tokenBQty']}" )
	else:
		print( f"Success: withdraw of token B succeeded" )
		score += 1	

	return score

def validate(student_repo_path):
	#Create the AMM contract based on the student's code
	try:
		AMM = createAMM(student_repo_path)
	except Exception as e:
		print( "Error: failed to create AMM" )
		print( e )
		return 0
	
	score_LP = check_LP(AMM)
	score_CT = check_trade(AMM,userA)
	score_WD = check_withdraw(AMM)

	assert score_LP in range(5)
	assert score_CT in range(7)
	assert score_WD in range(6)

	final_score = int( 100*(float(score_LP)/4 + float(score_CT)/6 + float(score_WD)/5)/3 )
	
	print( f"Final score = {final_score}" )
	return final_score


