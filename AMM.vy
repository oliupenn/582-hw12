from vyper.interfaces import ERC20

tokenAQty: public(uint256) #Quantity of tokenA held by the contract
tokenBQty: public(uint256) #Quantity of tokenB held by the contract

invariant: public(uint256) #The Constant-Function invariant (tokenAQty*tokenBQty = invariant throughout the life of the contract)
tokenA: ERC20 #The ERC20 contract for tokenA
tokenB: ERC20 #The ERC20 contract for tokenB
owner: public(address) #The liquidity provider (the address that has the right to withdraw funds and close the contract)

@external
def get_token_address(token: uint256) -> address:
	if token == 0:
		return self.tokenA.address
	if token == 1:
		return self.tokenB.address
	return ZERO_ADDRESS	

# Sets the on chain market maker with its owner, and initial token quantities
@external
def provideLiquidity(tokenA_addr: address, tokenB_addr: address, tokenA_quantity: uint256, tokenB_quantity: uint256):
	assert self.invariant == 0 #This ensures that liquidity can only be provided once
	self.tokenA = ERC20(tokenA_addr)
	self.tokenB = ERC20(tokenB_addr)
	self.owner = msg.sender
	self.tokenAQty = tokenA_quantity
	self.tokenBQty = tokenB_quantity
	self.tokenA.transferFrom(msg.sender, self, tokenA_quantity)
	self.tokenB.transferFrom(msg.sender, self, tokenB_quantity)
	self.invariant = tokenA_quantity * tokenB_quantity
	assert self.invariant > 0

# Trades one token for the other
@external
def tradeTokens(sell_token: address, sell_quantity: uint256):
	assert sell_token == self.tokenA.address or sell_token == self.tokenB.address

	if sell_token == self.tokenA.address:
		self.tokenA.transferFrom(msg.sender, self, sell_quantity)
		new_tokenAQty: uint256 = self.tokenAQty + sell_quantity
		new_tokenBQty: uint256 = self.invariant / new_tokenAQty
		tokenB_to_send: uint256 = self.tokenBQty - new_tokenBQty
		self.tokenB.transfer(msg.sender, tokenB_to_send)
		self.tokenAQty = new_tokenAQty
		self.tokenBQty = new_tokenBQty

	else:
		self.tokenB.transferFrom(msg.sender, self, sell_quantity)
		new_tokenBQty: uint256 = self.tokenBQty + sell_quantity
		new_tokenAQty: uint256 = self.invariant / new_tokenBQty
		tokenA_to_send: uint256 = self.tokenAQty - new_tokenAQty
		self.tokenA.transfer(msg.sender, tokenA_to_send)
		self.tokenBQty = new_tokenBQty
		self.tokenAQty = new_tokenAQty

# Owner can withdraw their funds and destroy the market maker
@external
def ownerWithdraw():
	assert self.owner == msg.sender
	self.tokenA.transfer(self.owner, self.tokenAQty)
	self.tokenB.transfer(self.owner, self.tokenBQty)
	selfdestruct(self.owner)
