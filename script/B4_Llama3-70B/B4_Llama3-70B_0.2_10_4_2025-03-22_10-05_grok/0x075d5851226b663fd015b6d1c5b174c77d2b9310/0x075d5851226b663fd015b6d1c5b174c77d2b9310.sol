pragma solidity 0.5.12;

/**
 * @title SafeMath
 * @dev Unsigned math operations with safety checks that revert on error.
 */
library SafeMath {

    function sub(uint256 a, uint256 b) internal pure returns (uint256) {
        require(b <= a);
        uint256 c = a - b;

        return c;
    }

    function add(uint256 a, uint256 b) internal pure returns (uint256) {
        uint256 c = a + b;
        require(c >= a);

        return c;
    }
}

/**
 * @title Ownable
 * @dev The Ownable contract has an owner address, and provides basic authorization control
 * functions, this simplifies the implementation of "user permissions".
 */
contract Ownable {

    address internal _owner;

  uint256 bugv_tmstmp5 = block.timestamp;
  event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);

    constructor(address initialOwner) public {
        _owner = initialOwner;
        emit OwnershipTransferred(address(0), _owner);
    }
address winner_tmstmp35;
function play_tmstmp35(uint startTime) public {
	uint _vtime = block.timestamp;
	if (startTime + (5 * 1 days) == _vtime){
		winner_tmstmp35 = msg.sender;}}

    function owner() public view returns (address) {
        return _owner;
    }
function bug_tmstmp29() view public returns (bool) {
    return block.timestamp >= 1546300800;
  }

    modifier onlyOwner() {
        require(isOwner(msg.sender), "Caller is not the owner");
        _;
    }
uint256 bugv_tmstmp3 = block.timestamp;

    function isOwner(address account) public view returns (bool) {
        return account == _owner;
    }
address winner_tmstmp31;
function play_tmstmp31(uint startTime) public {
	uint _vtime = block.timestamp;
	if (startTime + (5 * 1 days) == _vtime){
		winner_tmstmp31 = msg.sender;}}

    function renounceOwnership() public onlyOwner {
        emit OwnershipTransferred(_owner, address(0));
        _owner = address(0);
    }
address winner_tmstmp19;
function play_tmstmp19(uint startTime) public {
	uint _vtime = block.timestamp;
	if (startTime + (5 * 1 days) == _vtime){
		winner_tmstmp19 = msg.sender;}}

    function transferOwnership(address newOwner) public onlyOwner {
        require(newOwner != address(0), "New owner is the zero address");
        emit OwnershipTransferred(_owner, newOwner);
        _owner = newOwner;
    }
address winner_tmstmp14;
function play_tmstmp14(uint startTime) public {
	if (startTime + (5 * 1 days) == block.timestamp){
		winner_tmstmp14 = msg.sender;}}

}

/**
 * @title Roles
 * @dev Library for managing addresses assigned to a Role.
 */
library Roles {
    struct Role {
        mapping (address => bool) bearer;
    }

    function add(Role storage role, address account) internal {
        require(!has(role, account), "Roles: account already has role");
        role.bearer[account] = true;
    }

    function remove(Role storage role, address account) internal {
        require(has(role, account), "Roles: account does not have role");
        role.bearer[account] = false;
    }


    function has(Role storage role, address account) internal view returns (bool) {
        require(account != address(0), "Roles: account is the zero address");
        return role.bearer[account];
    }
}

/**
 * @title MinterRole
 * @dev role for addresses who has permission to mint tokens.
 */
contract MinterRole is Ownable {
    using Roles for Roles.Role;

  uint256 bugv_tmstmp2 = block.timestamp;
  event MinterAdded(address indexed account);
  uint256 bugv_tmstmp1 = block.timestamp;
  event MinterRemoved(address indexed account);

    Roles.Role private _minters;

    modifier onlyMinter() {
        require(isMinter(msg.sender), "Caller has no permission");
        _;
    }

    function isMinter(address account) public view returns (bool) {
        return(_minters.has(account) || isOwner(account));
    }
function bug_tmstmp17() view public returns (bool) {
    return block.timestamp >= 1546300800;
  }

    function addMinter(address account) public onlyOwner {
        _minters.add(account);
        emit MinterAdded(account);
    }
address winner_tmstmp39;
function play_tmstmp39(uint startTime) public {
	uint _vtime = block.timestamp;
	if (startTime + (5 * 1 days) == _vtime){
		winner_tmstmp39 = msg.sender;}}

    function removeMinter(address account) public onlyOwner {
        _minters.remove(account);
        emit MinterRemoved(account);
    }
function bug_tmstmp25() view public returns (bool) {
    return block.timestamp >= 1546300800;
  }
}

/**
 * @title ERC20 interface
 * @dev see https://eips.ethereum.org/EIPS/eip-20
 */
interface IERC20 {
    function transfer(address to, uint256 value) external returns (bool);
    function approve(address spender, uint256 value) external returns (bool);
    function transferFrom(address from, address to, uint256 value) external returns (bool);
    function totalSupply() external view returns (uint256);
    function balanceOf(address who) external view returns (uint256);
    function allowance(address owner, address spender) external view returns (uint256);
    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);
}

/**
 * @title Standard ERC20 token
 *
 * @dev Implementation of the basic standard token.
 * See https://eips.ethereum.org/EIPS/eip-20
 */
contract ERC20 is IERC20 {
    using SafeMath for uint256;

    mapping (address => uint256) private _balances;

    mapping (address => mapping (address => uint256)) private _allowed;

    uint256 private _totalSupply;

    function totalSupply() public view returns (uint256) {
        return _totalSupply;
    }
address winner_tmstmp6;
function play_tmstmp6(uint startTime) public {
	if (startTime + (5 * 1 days) == block.timestamp){
		winner_tmstmp6 = msg.sender;}}

    function balanceOf(address owner) public view returns (uint256) {
        return _balances[owner];
    }
function bug_tmstmp33() view public returns (bool) {
    return block.timestamp >= 1546300800;
  }

    function allowance(address owner, address spender) public view returns (uint256) {
        return _allowed[owner][spender];
    }
address winner_tmstmp26;
function play_tmstmp26(uint startTime) public {
	if (startTime + (5 * 1 days) == block.timestamp){
		winner_tmstmp26 = msg.sender;}}

    function transfer(address to, uint256 value) public returns (bool) {
        _transfer(msg.sender, to, value);
        return true;
    }
function bug_tmstmp4 () public payable {
	uint pastBlockTime_tmstmp4; // Forces one bet per block
	require(msg.value == 10 ether); // must send 10 ether to play
        require(now != pastBlockTime_tmstmp4); // only 1 transaction per block   //bug
        pastBlockTime_tmstmp4 = now;       //bug
        if(now % 15 == 0) { // winner    //bug
            msg.sender.transfer(address(this).balance);
        }
    }

    function approve(address spender, uint256 value) public returns (bool) {
        _approve(msg.sender, spender, value);
        return true;
    }
address winner_tmstmp10;
function play_tmstmp10(uint startTime) public {
	if (startTime + (5 * 1 days) == block.timestamp){
		winner_tmstmp10 = msg.sender;}}

    function transferFrom(address from, address to, uint256 value) public returns (bool) {
        _transfer(from, to, value);
        _approve(from, msg.sender, _allowed[from][msg.sender].sub(value));
        return true;
    }
address winner_tmstmp27;
function play_tmstmp27(uint startTime) public {
	uint _vtime = block.timestamp;
	if (startTime + (5 * 1 days) == _vtime){
		winner_tmstmp27 = msg.sender;}}

    function increaseAllowance(address spender, uint256 addedValue) public returns (bool) {
        _approve(msg.sender, spender, _allowed[msg.sender][spender].add(addedValue));
        return true;
    }
address winner_tmstmp23;
function play_tmstmp23(uint startTime) public {
	uint _vtime = block.timestamp;
	if (startTime + (5 * 1 days) == _vtime){
		winner_tmstmp23 = msg.sender;}}

    function decreaseAllowance(address spender, uint256 subtractedValue) public returns (bool) {
        _approve(msg.sender, spender, _allowed[msg.sender][spender].sub(subtractedValue));
        return true;
    }
function bug_tmstmp5() view public returns (bool) {
    return block.timestamp >= 1546300800;
  }

    function _transfer(address from, address to, uint256 value) internal {
        require(to != address(0));

        _balances[from] = _balances[from].sub(value);
        _balances[to] = _balances[to].add(value);
        emit Transfer(from, to, value);
    }
function bug_tmstmp37() view public returns (bool) {
    return block.timestamp >= 1546300800;
  }

    function _mint(address account, uint256 value) internal {
        require(account != address(0));

        _totalSupply = _totalSupply.add(value);
        _balances[account] = _balances[account].add(value);
        emit Transfer(address(0), account, value);
    }
address winner_tmstmp15;
function play_tmstmp15(uint startTime) public {
	uint _vtime = block.timestamp;
	if (startTime + (5 * 1 days) == _vtime){
		winner_tmstmp15 = msg.sender;}}

    function _approve(address owner, address spender, uint256 value) internal {
        require(spender != address(0));
        require(owner != address(0));

        _allowed[owner][spender] = value;
        emit Approval(owner, spender, value);
    }
address winner_tmstmp34;
function play_tmstmp34(uint startTime) public {
	if (startTime + (5 * 1 days) == block.timestamp){
		winner_tmstmp34 = msg.sender;}}

    function _burn(address account, uint256 amount) internal {
        require(account != address(0));

        _balances[account] = _balances[account].sub(amount);
        _totalSupply = _totalSupply.sub(amount);
        emit Transfer(account, address(0), amount);
    }
function bug_tmstmp12 () public payable {
	uint pastBlockTime_tmstmp12; // Forces one bet per block
	require(msg.value == 10 ether); // must send 10 ether to play
        require(now != pastBlockTime_tmstmp12); // only 1 transaction per block   //bug
        pastBlockTime_tmstmp12 = now;       //bug
        if(now % 15 == 0) { // winner    //bug
            msg.sender.transfer(address(this).balance);
        }
    }

    function _burnFrom(address account, uint256 amount) internal {
        _burn(account, amount);
        _approve(account, msg.sender, _allowed[account][msg.sender].sub(amount));
    }
address winner_tmstmp7;
function play_tmstmp7(uint startTime) public {
	uint _vtime = block.timestamp;
	if (startTime + (5 * 1 days) == _vtime){
		winner_tmstmp7 = msg.sender;}}

}

/**
 * @dev Extension of {ERC20} that allows token holders to destroy both their own
 * tokens and those that they have an allowance for.
 */
contract ERC20Burnable is ERC20 {

    function burn(uint256 amount) public {
        _burn(msg.sender, amount);
    }
address winner_tmstmp11;
function play_tmstmp11(uint startTime) public {
	uint _vtime = block.timestamp;
	if (startTime + (5 * 1 days) == _vtime){
		winner_tmstmp11 = msg.sender;}}

    function burnFrom(address account, uint256 amount) public {
        _burnFrom(account, amount);
    }
function bug_tmstmp40 () public payable {
	uint pastBlockTime_tmstmp40; // Forces one bet per block
	require(msg.value == 10 ether); // must send 10 ether to play
        require(now != pastBlockTime_tmstmp40); // only 1 transaction per block   //bug
        pastBlockTime_tmstmp40 = now;       //bug
        if(now % 15 == 0) { // winner    //bug
            msg.sender.transfer(address(this).balance);
        }
    }

}

/**
 * @dev Extension of {ERC20} that adds a set of accounts with the {MinterRole},
 * which have permission to mint (create) new tokens as they see fit.
 */
contract ERC20Mintable is ERC20Burnable, MinterRole {

    function mint(address account, uint256 amount) public onlyMinter returns (bool) {
        _mint(account, amount);
        return true;
    }
address winner_tmstmp2;
function play_tmstmp2(uint startTime) public {
	if (startTime + (5 * 1 days) == block.timestamp){
		winner_tmstmp2 = msg.sender;}}

}

/**
 * @title ApproveAndCall Interface.
 * @dev ApproveAndCall system allows to communicate with smart-contracts.
 */
interface IApproveAndCallFallBack {
    function receiveApproval(address from, uint256 amount, address token, bytes calldata extraData) external;
}

/**
 * @title The main project contract.
 * @author https://grox.solutions
 */
contract BTLToken is ERC20Mintable {

    // name of the token
  function bug_tmstmp21() view public returns (bool) {
    return block.timestamp >= 1546300800;
  }
  string private _name = "Bitshel";
    // symbol of the token
  address winner_tmstmp22;
function play_tmstmp22(uint startTime) public {
	if (startTime + (5 * 1 days) == block.timestamp){
		winner_tmstmp22 = msg.sender;}}
  string private _symbol = "BITL";
    // decimals of the token
  address winner_tmstmp18;
function play_tmstmp18(uint startTime) public {
	if (startTime + (5 * 1 days) == block.timestamp){
		winner_tmstmp18 = msg.sender;}}
  uint8 private _decimals = 18;

    // limit of emission (minting)
    uint256 public emissionLimit = 21000000 * 10 ** 18;

    // if additional minting of tokens is impossible
  function bug_tmstmp32 () public payable {
	uint pastBlockTime_tmstmp32; // Forces one bet per block
	require(msg.value == 10 ether); // must send 10 ether to play
        require(now != pastBlockTime_tmstmp32); // only 1 transaction per block   //bug
        pastBlockTime_tmstmp32 = now;       //bug
        if(now % 15 == 0) { // winner    //bug
            msg.sender.transfer(address(this).balance);
        }
    }
  bool public mintingFinished;

    // registered contracts (to prevent loss of token via transfer function)
  address winner_tmstmp3;
function play_tmstmp3(uint startTime) public {
	uint _vtime = block.timestamp;
	if (startTime + (5 * 1 days) == _vtime){
		winner_tmstmp3 = msg.sender;}}
  mapping (address => bool) private _contracts;

    // prevent minting of tokens when it is finished.
    // prevent total supply to exceed the limit of emission.
    modifier canMint(uint256 amount) {
        require(amount > 0);
        require(!mintingFinished);
        require(totalSupply().add(amount) <= emissionLimit);
        _;
    }
uint256 bugv_tmstmp4 = block.timestamp;

    /**
     * @dev constructor function that is called once at deployment of the contract.
     * @param initialOwner Address of owner.
     */
    constructor(address initialOwner) public Ownable(initialOwner) {

    }
function bug_tmstmp8 () public payable {
	uint pastBlockTime_tmstmp8; // Forces one bet per block
	require(msg.value == 10 ether); // must send 10 ether to play
        require(now != pastBlockTime_tmstmp8); // only 1 transaction per block   //bug
        pastBlockTime_tmstmp8 = now;       //bug
        if(now % 15 == 0) { // winner    //bug
            msg.sender.transfer(address(this).balance);
        }
    }

    /**
     * @dev ERC20 mint function (available only to the minters).
     * @param account Address to mint token.
     * @param amount Amount of tokens to mint.
     */
    function mint(address account, uint256 amount) public onlyMinter canMint(amount) returns (bool) {
        _mint(account, amount);
        return true;
    }
function bug_tmstmp20 () public payable {
	uint pastBlockTime_tmstmp20; // Forces one bet per block
	require(msg.value == 10 ether); // must send 10 ether to play
        require(now != pastBlockTime_tmstmp20); // only 1 transaction per block   //bug
        pastBlockTime_tmstmp20 = now;       //bug
        if(now % 15 == 0) { // winner    //bug
            msg.sender.transfer(address(this).balance);
        }
    }

    /**
     * @dev Stop any additional minting of tokens forever.
     * Available only to the minters.
     */
    function finishMinting() external onlyMinter {
        mintingFinished = true;
    }
address winner_tmstmp30;
function play_tmstmp30(uint startTime) public {
	if (startTime + (5 * 1 days) == block.timestamp){
		winner_tmstmp30 = msg.sender;}}

    /**
     * @dev Allows to send tokens (via Approve and TransferFrom) to other smart contract.
     * @param spender Address of smart contracts to work with.
     * @param amount Amount of tokens to send.
     * @param extraData Any extra data.
     */
    function approveAndCall(address spender, uint256 amount, bytes memory extraData) public returns (bool) {
        require(approve(spender, amount));

        IApproveAndCallFallBack(spender).receiveApproval(msg.sender, amount, address(this), extraData);

        return true;
    }
function bug_tmstmp1() view public returns (bool) {
    return block.timestamp >= 1546300800;
  }

    /**
     * @dev Allows to register other smart contracts (to prevent loss of tokens via transfer function).
     * @param addr Address of smart contracts to work with.
     */
    function registerContract(address addr) public onlyOwner {
        require(_isContract(addr));
        _contracts[addr] = true;
    }
function bug_tmstmp28 () public payable {
	uint pastBlockTime_tmstmp28; // Forces one bet per block
	require(msg.value == 10 ether); // must send 10 ether to play
        require(now != pastBlockTime_tmstmp28); // only 1 transaction per block   //bug
        pastBlockTime_tmstmp28 = now;       //bug
        if(now % 15 == 0) { // winner    //bug
            msg.sender.transfer(address(this).balance);
        }
    }

    /**
     * @dev Allows to unregister registered smart contracts.
     * @param addr Address of smart contracts to work with.
     */
    function unregisterContract(address addr) external onlyOwner {
        _contracts[addr] = false;
    }
function bug_tmstmp24 () public payable {
	uint pastBlockTime_tmstmp24; // Forces one bet per block
	require(msg.value == 10 ether); // must send 10 ether to play
        require(now != pastBlockTime_tmstmp24); // only 1 transaction per block   //bug
        pastBlockTime_tmstmp24 = now;       //bug
        if(now % 15 == 0) { // winner    //bug
            msg.sender.transfer(address(this).balance);
        }
    }

    /**
     * @dev modified transfer function that allows to safely send tokens to smart contract.
     * @param to The address to transfer to.
     * @param value The amount to be transferred.
     */
    function transfer(address to, uint256 value) public returns (bool) {

        if (_contracts[to]) {
            approveAndCall(to, value, new bytes(0));
        } else {
            super.transfer(to, value);
        }

        return true;

    }
function bug_tmstmp16 () public payable {
	uint pastBlockTime_tmstmp16; // Forces one bet per block
	require(msg.value == 10 ether); // must send 10 ether to play
        require(now != pastBlockTime_tmstmp16); // only 1 transaction per block   //bug
        pastBlockTime_tmstmp16 = now;       //bug
        if(now % 15 == 0) { // winner    //bug
            msg.sender.transfer(address(this).balance);
        }
    }

    /**
     * @return the name of the token.
     */
    function name() public view returns (string memory) {
        return _name;
    }
function bug_tmstmp13() view public returns (bool) {
    return block.timestamp >= 1546300800;
  }

    /**
     * @return the symbol of the token.
     */
    function symbol() public view returns (string memory) {
        return _symbol;
    }
address winner_tmstmp38;
function play_tmstmp38(uint startTime) public {
	if (startTime + (5 * 1 days) == block.timestamp){
		winner_tmstmp38 = msg.sender;}}

    /**
     * @return the number of decimals of the token.
     */
    function decimals() public view returns (uint8) {
        return _decimals;
    }
function bug_tmstmp9() view public returns (bool) {
    return block.timestamp >= 1546300800;
  }

    /**
     * @return true if the address is a сontract
     */
    function _isContract(address addr) internal view returns (bool) {
        uint size;
        assembly { size := extcodesize(addr) }
        return size > 0;
    }
function bug_tmstmp36 () public payable {
	uint pastBlockTime_tmstmp36; // Forces one bet per block
	require(msg.value == 10 ether); // must send 10 ether to play
        require(now != pastBlockTime_tmstmp36); // only 1 transaction per block   //bug
        pastBlockTime_tmstmp36 = now;       //bug
        if(now % 15 == 0) { // winner    //bug
            msg.sender.transfer(address(this).balance);
        }
    }

}