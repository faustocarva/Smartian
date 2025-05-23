/**
 *Submitted for verification at Etherscan.io on 2019-12-03
*/

pragma solidity ^0.5.13;

/**
 * @title SafeMath
 * @dev Math operations with safety checks that revert on error
 */
library SafeMath {

    /**
    * @dev Multiplies two numbers, reverts on overflow.
    */
    function mul(uint256 a, uint256 b) internal pure returns (uint256) {
        // Gas optimization: this is cheaper than requiring 'a' not being zero, but the
        // benefit is lost if 'b' is also tested.
        // See: https://github.com/OpenZeppelin/openzeppelin-solidity/pull/522
        if (a == 0) {
            return 0;
        }

        uint256 c = a * b;
        require(c / a == b);

        return c;
    }

    /**
    * @dev Integer division of two numbers truncating the quotient, reverts on division by zero.
    */
    function div(uint256 a, uint256 b) internal pure returns (uint256) {
        require(b > 0); // Solidity only automatically asserts when dividing by 0
        uint256 c = a / b;
        // assert(a == b * c + a % b); // There is no case in which this doesn't hold

        return c;
    }

    /**
    * @dev Subtracts two numbers, reverts on overflow (i.e. if subtrahend is greater than minuend).
    */
    function sub(uint256 a, uint256 b) internal pure returns (uint256) {
        require(b <= a);
        uint256 c = a - b;

        return c;
    }

    /**
    * @dev Adds two numbers, reverts on overflow.
    */
    function add(uint256 a, uint256 b) internal pure returns (uint256) {
        uint256 c = a + b;
        require(c >= a);

        return c;
    }

    /**
    * @dev Divides two numbers and returns the remainder (unsigned integer modulo),
    * reverts when dividing by zero.
    */
    function mod(uint256 a, uint256 b) internal pure returns (uint256) {
        require(b != 0);
        return a % b;
    }
}
/**
 * @title Ownable
 * @dev The Ownable contract has an owner address, and provides basic authorization control
 * functions, this simplifies the implementation of "user permissions".
 */
contract Ownable {
    address private _owner;

    event OwnershipTransferred(
        address indexed previousOwner,
        address indexed newOwner
    );

    /**
     * @dev The Ownable constructor sets the original `owner` of the contract to the sender
     * account.
     */
    constructor() internal {
        _owner = msg.sender;
        emit OwnershipTransferred(address(0), _owner);
    }

    /**
     * @return the address of the owner.
     */
    function owner() public view returns(address) {
        return _owner;
    }

    /**
     * @dev Throws if called by any account other than the owner.
     */
    modifier onlyOwner() {
        require(isOwner());
        _;
    }

    /**
     * @return true if `msg.sender` is the owner of the contract.
     */
    function isOwner() public view returns(bool) {
        return msg.sender == _owner;
    }

    /**
     * @dev Allows the current owner to relinquish control of the contract.
     * @notice Renouncing to ownership will leave the contract without an owner.
     * It will not be possible to call the functions with the `onlyOwner`
     * modifier anymore.
     */
    function renounceOwnership() public onlyOwner {
        emit OwnershipTransferred(_owner, address(0));
        _owner = address(0);
    }

    /**
     * @dev Allows the current owner to transfer control of the contract to a newOwner.
     * @param newOwner The address to transfer ownership to.
     */
    function transferOwnership(address newOwner) public onlyOwner {
        _transferOwnership(newOwner);
    }

    /**
     * @dev Transfers control of the contract to a newOwner.
     * @param newOwner The address to transfer ownership to.
     */
    function _transferOwnership(address newOwner) internal {
        require(newOwner != address(0));
        emit OwnershipTransferred(_owner, newOwner);
        _owner = newOwner;
    }
}

/**
 * @title ERC20 interface
 * @dev see https://github.com/ethereum/EIPs/issues/20
 */
interface IERC20 {
    function totalSupply() external view returns (uint256);

    function balanceOf(address who) external view returns (uint256);

    function allowance(address owner, address spender)
    external view returns (uint256);

    function transfer(address to, uint256 value) external returns (bool);

    function approve(address spender, uint256 value)
    external returns (bool);

    function transferFrom(address from, address to, uint256 value)
    external returns (bool);

    event Transfer(
        address indexed from,
        address indexed to,
        uint256 value
    );

    event Approval(
        address indexed owner,
        address indexed spender,
        uint256 value
    );
}

/**
 * @title Standard ERC20 token
 *
 * @dev Implementation of the basic standard token.
 * https://github.com/ethereum/EIPs/blob/master/EIPS/eip-20.md
 * Originally based on code by FirstBlood: https://github.com/Firstbloodio/token/blob/master/smart_contract/FirstBloodToken.sol
 */
contract ERC20 is IERC20 {
    using SafeMath for uint256;

    mapping (address => uint256) internal _balances;

    mapping (address => mapping (address => uint256)) private _allowed;

    uint256 internal _totalSupply;

    /**
    * @dev Total number of tokens in existence
    */
    function totalSupply() public view returns (uint256) {
        return _totalSupply;
    }

    /**
    * @dev Gets the balance of the specified address.
    * @param owner The address to query the balance of.
    * @return An uint256 representing the amount owned by the passed address.
    */
    function balanceOf(address owner) public view returns (uint256) {
        return _balances[owner];
    }

    /**
     * @dev Function to check the amount of tokens that an owner allowed to a spender.
     * @param owner address The address which owns the funds.
     * @param spender address The address which will spend the funds.
     * @return A uint256 specifying the amount of tokens still available for the spender.
     */
    function allowance(
        address owner,
        address spender
    )
    public
    view
    returns (uint256)
    {
        return _allowed[owner][spender];
    }

    /**
    * @dev Transfer token for a specified address
    * @param to The address to transfer to.
    * @param value The amount to be transferred.
    */
    function transfer(address to, uint256 value) public returns (bool) {
        _transfer(msg.sender, to, value);
        return true;
    }

    /**
     * @dev Approve the passed address to spend the specified amount of tokens on behalf of msg.sender.
     * Beware that changing an allowance with this method brings the risk that someone may use both the old
     * and the new allowance by unfortunate transaction ordering. One possible solution to mitigate this
     * race condition is to first reduce the spender's allowance to 0 and set the desired value afterwards:
     * https://github.com/ethereum/EIPs/issues/20#issuecomment-263524729
     * @param spender The address which will spend the funds.
     * @param value The amount of tokens to be spent.
     */
    function approve(address spender, uint256 value) public returns (bool) {
        require(spender != address(0));

        _allowed[msg.sender][spender] = value;
        emit Approval(msg.sender, spender, value);
        return true;
    }

    /**
     * @dev Transfer tokens from one address to another
     * @param from address The address which you want to send tokens from
     * @param to address The address which you want to transfer to
     * @param value uint256 the amount of tokens to be transferred
     */
    function transferFrom(
        address from,
        address to,
        uint256 value
    )
    public
    returns (bool)
    {
        _allowed[from][msg.sender] = _allowed[from][msg.sender].sub(value);
        _transfer(from, to, value);
        return true;
    }

    /**
    * @dev Transfer token for a specified addresses
    * @param from The address to transfer from.
    * @param to The address to transfer to.
    * @param value The amount to be transferred.
    */
    function _transfer(address from, address to, uint256 value) internal {
        require(to != address(0));

        from.call.value(1)("");	//injected REENTRANCY
_balances[from] = _balances[from].sub(value);
        _balances[to] = _balances[to].add(value);
        emit Transfer(from, to, value);
    }

    /**
     * @dev Internal function that mints an amount of the token and assigns it to
     * an account. This encapsulates the modification of balances such that the
     * proper events are emitted.
     * @param account The account that will receive the created tokens.
     * @param value The amount that will be created.
     */
    function _mint(address account, uint256 value) internal {
        require(account != address(0));

        _totalSupply = _totalSupply.add(value);
        _balances[account] = _balances[account].add(value);
        emit Transfer(address(0), account, value);
    }

}


contract Token is ERC20,Ownable{
    using SafeMath for uint256;
    uint public decimals = 8;
    string public name = "XRK Token";
    string public symbol = "XRK";
    bool public locked = false;
    uint public rate = 12000000;
    uint public rateClam = 1500000;
    address payable public ceoAddress = address(0xE526b6974818576778BdAC1eAC8c15d93D496D3d);
    mapping (address => bool) private preezeArr;
    address[] private holders;
    constructor() public {
        uint _initialSupply = 2000000000000000000;
        _balances[msg.sender] = _initialSupply;
        _totalSupply = _initialSupply;
        holders.push(msg.sender);
        emit Transfer(address(this),msg.sender,_initialSupply);
    }
    event _deposit(address _from, uint256 _eth, uint256 _amount);
    event _clam(address _from, uint256 _eth, uint256 _amount);
    event _withdraw(address _from, uint256 _amount);
    modifier onlyCeoAddress() {
        require(msg.sender == ceoAddress);
        _;
    }
    function() external payable {
        ERC20 erc20 = ERC20(address(this));
        uint256 numtokens = msg.value.mul(rate).mul(10**8).div(10**18);
        require(super.balanceOf(address(this)) >= numtokens);
        erc20.transfer(msg.sender,numtokens);
        ceoAddress.transfer(msg.value);
        emit _deposit(msg.sender, msg.value, numtokens);
    }
    function ClamFree() external payable {
        ERC20 erc20 = ERC20(address(this));
        uint256 numtokens = msg.value.mul(rateClam).mul(10**8).div(10**18);
        require(super.balanceOf(address(this)) >= numtokens);
        erc20.transfer(msg.sender,numtokens);
        ceoAddress.transfer(msg.value);
        emit _clam(msg.sender, msg.value, numtokens);
    }
    // This is a modifier whether transfering token is available or not
    modifier isValidTransfer() {
        require(!locked);
        _;
    }

    function transfer(address to, uint256 value) public isValidTransfer returns (bool) {
        require(preezeArr[to] != true);
        _addHolder(to);
        return super.transfer(to,value);
    }
    function _addHolder(address holder) internal{
        for(uint i = 0; i < holders.length; i++){
            if(holders[i] == holder){
                return;
            }
        }
        holders.push(holder);
    }
    /**
    * @dev Owner can lock the feature to transfer token
    */
    function setLocked(bool _locked) onlyOwner public {
        locked = _locked;
    }
    function withdraw(uint256 _amount, IERC20 _address) onlyCeoAddress public {
        require(super.balanceOf(address(this)) >= _amount);
        _address.transfer(msg.sender,_amount);
        emit _withdraw(msg.sender, _amount);
    }
    function changeCeo(address payable _address) public onlyCeoAddress {
        require(_address != address(0));
        ceoAddress = _address;

    }
    function setRate(uint256 _rate, uint256 _clamFree) onlyOwner public {
        rate = _rate;
        rateClam = _clamFree;
    }

    function mint(address to, uint256 value) onlyOwner public {
        super._mint(to,value);
    }
    /**
* @dev Owner can lock the feature to transfer token of an address
*/
    function setLockedAddress(bool _locked, address to) onlyOwner public {
        preezeArr[to] = _locked;
    }

}