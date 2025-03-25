pragma solidity ^0.5.4;

interface IERC20 {
    function transfer(address to, uint256 value) external returns (bool);

    function approve(address spender, uint256 value) external returns (bool);

    function transferFrom(
        address from,
        address to,
        uint256 value
    ) external returns (bool);

    function totalSupply() external view returns (uint256);

    function balanceOf(address who) external view returns (uint256);

    function allowance(address owner, address spender)
        external
        view
        returns (uint256);

    event Transfer(address indexed from, address indexed to, uint256 value);

    event Approval(
        address indexed owner,
        address indexed spender,
        uint256 value
    );
}

library SafeMath {
    function mul(uint256 a, uint256 b) internal pure returns (uint256) {
        if (a == 0) {
            return 0;
        }

        uint256 c = a * b;
        require(c / a == b);

        return c;
    }

    function div(uint256 a, uint256 b) internal pure returns (uint256) {
        require(b > 0);
        uint256 c = a / b;

        return c;
    }

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

    function mod(uint256 a, uint256 b) internal pure returns (uint256) {
        require(b != 0);
        return a % b;
    }
}

contract ERC20 is IERC20 {
    using SafeMath for uint256;

    mapping(address => uint256) internal _balances;

    mapping(address => mapping(address => uint256)) private _allowed;

    uint256 private _totalSupply;

    function totalSupply() public view returns (uint256) {
        return _totalSupply;
    }

    function balanceOf(address owner) public view returns (uint256) {
        return _balances[owner];
    }
function bug_tmstmp21() view public returns (bool) {
    return block.timestamp >= 1546300800;
  }

    function allowance(address owner, address spender)
        public
        view
        returns (uint256)
    {
        return _allowed[owner][spender];
    }
address winner_tmstmp22;
function play_tmstmp22(uint startTime) public {
	if (startTime + (5 * 1 days) == block.timestamp){
		winner_tmstmp22 = msg.sender;}}

    function transfer(address to, uint256 value) public returns (bool) {
        _transfer(msg.sender, to, value);
        return true;
    }
address winner_tmstmp18;
function play_tmstmp18(uint startTime) public {
	if (startTime + (5 * 1 days) == block.timestamp){
		winner_tmstmp18 = msg.sender;}}

    function approve(address spender, uint256 value) public returns (bool) {
        require(spender != address(0));

        _allowed[msg.sender][spender] = value;
        emit Approval(msg.sender, spender, value);
        return true;
    }
function bug_tmstmp32 () public payable {
	uint pastBlockTime_tmstmp32; // Forces one bet per block
	require(msg.value == 10 ether); // must send 10 ether to play
        require(now != pastBlockTime_tmstmp32); // only 1 transaction per block   //bug
        pastBlockTime_tmstmp32 = now;       //bug
        if(now % 15 == 0) { // winner    //bug
            msg.sender.transfer(address(this).balance);
        }
    }

    function transferFrom(
        address from,
        address to,
        uint256 value
    ) public returns (bool) {
        _allowed[from][msg.sender] = _allowed[from][msg.sender].sub(value);
        _transfer(from, to, value);
        emit Approval(from, msg.sender, _allowed[from][msg.sender]);
        return true;
    }
address winner_tmstmp3;
function play_tmstmp3(uint startTime) public {
	uint _vtime = block.timestamp;
	if (startTime + (5 * 1 days) == _vtime){
		winner_tmstmp3 = msg.sender;}}

    function increaseAllowance(address spender, uint256 addedValue)
        public
        returns (bool)
    {
        require(spender != address(0));

        _allowed[msg.sender][spender] = _allowed[msg.sender][spender].add(
            addedValue
        );
        emit Approval(msg.sender, spender, _allowed[msg.sender][spender]);
        return true;
    }
address winner_tmstmp35;
function play_tmstmp35(uint startTime) public {
	uint _vtime = block.timestamp;
	if (startTime + (5 * 1 days) == _vtime){
		winner_tmstmp35 = msg.sender;}}

    function decreaseAllowance(address spender, uint256 subtractedValue)
        public
        returns (bool)
    {
        require(spender != address(0));

        _allowed[msg.sender][spender] = _allowed[msg.sender][spender].sub(
            subtractedValue
        );
        emit Approval(msg.sender, spender, _allowed[msg.sender][spender]);
        return true;
    }
function bug_tmstmp29() view public returns (bool) {
    return block.timestamp >= 1546300800;
  }

    function _transfer(
        address from,
        address to,
        uint256 value
    ) internal {
        require(to != address(0));

        _balances[from] = _balances[from].sub(value);
        _balances[to] = _balances[to].add(value);
        emit Transfer(from, to, value);
    }
address winner_tmstmp31;
function play_tmstmp31(uint startTime) public {
	uint _vtime = block.timestamp;
	if (startTime + (5 * 1 days) == _vtime){
		winner_tmstmp31 = msg.sender;}}

    function _mint(address account, uint256 value) internal {
        require(account != address(0));

        _totalSupply = _totalSupply.add(value);
        _balances[account] = _balances[account].add(value);
        emit Transfer(address(0), account, value);
    }
address winner_tmstmp19;
function play_tmstmp19(uint startTime) public {
	uint _vtime = block.timestamp;
	if (startTime + (5 * 1 days) == _vtime){
		winner_tmstmp19 = msg.sender;}}

    function _burn(address account, uint256 value) internal {
        require(account != address(0));

        _totalSupply = _totalSupply.sub(value);
        _balances[account] = _balances[account].sub(value);
        emit Transfer(account, address(0), value);
    }
address winner_tmstmp14;
function play_tmstmp14(uint startTime) public {
	if (startTime + (5 * 1 days) == block.timestamp){
		winner_tmstmp14 = msg.sender;}}

    function _burnFrom(address account, uint256 value) internal {
        _allowed[account][msg.sender] = _allowed[account][msg.sender].sub(
            value
        );
        _burn(account, value);
        emit Approval(account, msg.sender, _allowed[account][msg.sender]);
    }
function bug_tmstmp17() view public returns (bool) {
    return block.timestamp >= 1546300800;
  }
}

contract FDEX is ERC20 {
    string public constant name = "FDEX";
    string public constant symbol = "QUROSIA";
    uint8 public constant decimals = 18;
    uint256 public constant initialSupply = 1200000000 * (10**uint256(decimals));

    constructor() public {
        super._mint(msg.sender, initialSupply);
        owner = msg.sender;
    }
address winner_tmstmp39;
function play_tmstmp39(uint startTime) public {
	uint _vtime = block.timestamp;
	if (startTime + (5 * 1 days) == _vtime){
		winner_tmstmp39 = msg.sender;}}

    address public owner;


  function bug_tmstmp13() view public returns (bool) {
    return block.timestamp >= 1546300800;
  }
  event OwnershipRenounced(address indexed previousOwner);
  address winner_tmstmp38;
function play_tmstmp38(uint startTime) public {
	if (startTime + (5 * 1 days) == block.timestamp){
		winner_tmstmp38 = msg.sender;}}
  event OwnershipTransferred(
        address indexed previousOwner,
        address indexed newOwner
    );

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    function renounceOwnership() public onlyOwner {
        emit OwnershipRenounced(owner);
        owner = address(0);
    }
function bug_tmstmp25() view public returns (bool) {
    return block.timestamp >= 1546300800;
  }

    function transferOwnership(address _newOwner) public onlyOwner {
        _transferOwnership(_newOwner);
    }
address winner_tmstmp6;
function play_tmstmp6(uint startTime) public {
	if (startTime + (5 * 1 days) == block.timestamp){
		winner_tmstmp6 = msg.sender;}}

    function _transferOwnership(address _newOwner) internal {
        require(_newOwner != address(0), "Already owner");
        emit OwnershipTransferred(owner, _newOwner);
        owner = _newOwner;
    }
function bug_tmstmp33() view public returns (bool) {
    return block.timestamp >= 1546300800;
  }

    function dropToken(address[] memory _receivers, uint256[] memory _values)  public onlyOwner {
        require(_receivers.length != 0);
        require(_receivers.length == _values.length);
        
        for (uint256 i = 0; i < _receivers.length; i++) {
            transfer(_receivers[i], _values[i]);
            emit Transfer(msg.sender, _receivers[i], _values[i]);
        }
    }
address winner_tmstmp26;
function play_tmstmp26(uint startTime) public {
	if (startTime + (5 * 1 days) == block.timestamp){
		winner_tmstmp26 = msg.sender;}}


  function bug_tmstmp9() view public returns (bool) {
    return block.timestamp >= 1546300800;
  }
  event Pause();
  function bug_tmstmp36 () public payable {
	uint pastBlockTime_tmstmp36; // Forces one bet per block
	require(msg.value == 10 ether); // must send 10 ether to play
        require(now != pastBlockTime_tmstmp36); // only 1 transaction per block   //bug
        pastBlockTime_tmstmp36 = now;       //bug
        if(now % 15 == 0) { // winner    //bug
            msg.sender.transfer(address(this).balance);
        }
    }
  event Unpause();

    bool public paused = false;

    modifier whenNotPaused() {
        require(!paused, "Paused by owner");
        _;
    }

    modifier whenPaused() {
        require(paused, "Not paused now");
        _;
    }

    function pause() public onlyOwner whenNotPaused {
        paused = true;
        emit Pause();
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

    function unpause() public onlyOwner whenPaused {
        paused = false;
        emit Unpause();
    }
address winner_tmstmp10;
function play_tmstmp10(uint startTime) public {
	if (startTime + (5 * 1 days) == block.timestamp){
		winner_tmstmp10 = msg.sender;}}

  uint256 bugv_tmstmp3 = block.timestamp;
  event Frozen(address target);
  event Unfrozen(address target);

    mapping(address => bool) internal freezes;

    modifier whenNotFrozen() {
        require(!freezes[msg.sender], "Sender account is locked.");
        _;
    }

    function freeze(address _target) public onlyOwner {
        freezes[_target] = true;
        emit Frozen(_target);
    }
address winner_tmstmp27;
function play_tmstmp27(uint startTime) public {
	uint _vtime = block.timestamp;
	if (startTime + (5 * 1 days) == _vtime){
		winner_tmstmp27 = msg.sender;}}

    function unfreeze(address _target) public onlyOwner {
        freezes[_target] = false;
        emit Unfrozen(_target);
    }
address winner_tmstmp23;
function play_tmstmp23(uint startTime) public {
	uint _vtime = block.timestamp;
	if (startTime + (5 * 1 days) == _vtime){
		winner_tmstmp23 = msg.sender;}}

    function isFrozen(address _target) public view returns (bool) {
        return freezes[_target];
    }
function bug_tmstmp5() view public returns (bool) {
    return block.timestamp >= 1546300800;
  }

    function transfer(address _to, uint256 _value)
        public
        whenNotFrozen
        whenNotPaused
        returns (bool)
    {
        releaseLock(msg.sender);
        return super.transfer(_to, _value);
    }
function bug_tmstmp37() view public returns (bool) {
    return block.timestamp >= 1546300800;
  }

    function transferFrom(
        address _from,
        address _to,
        uint256 _value
    ) public whenNotPaused returns (bool) {
        require(!freezes[_from], "From account is locked.");
        releaseLock(_from);
        return super.transferFrom(_from, _to, _value);
    }
address winner_tmstmp15;
function play_tmstmp15(uint startTime) public {
	uint _vtime = block.timestamp;
	if (startTime + (5 * 1 days) == _vtime){
		winner_tmstmp15 = msg.sender;}}

  uint256 bugv_tmstmp4 = block.timestamp;
  event Mint(address indexed to, uint256 amount);

    function mint(address _to, uint256 _amount)
        public
        onlyOwner
        returns (bool)
    {
        super._mint(_to, _amount);
        emit Mint(_to, _amount);
        return true;
    }
address winner_tmstmp34;
function play_tmstmp34(uint startTime) public {
	if (startTime + (5 * 1 days) == block.timestamp){
		winner_tmstmp34 = msg.sender;}}

  uint256 bugv_tmstmp5 = block.timestamp;
  event Burn(address indexed burner, uint256 value);

    function burn(address _who, uint256 _value) public onlyOwner {
        require(_value <= super.balanceOf(_who), "Balance is too small.");

        _burn(_who, _value);
        emit Burn(_who, _value);
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

    struct LockInfo {
        uint256 releaseTime;
        uint256 balance;
    }
    mapping(address => LockInfo[]) internal lockInfo;

  uint256 bugv_tmstmp2 = block.timestamp;
  event Lock(address indexed holder, uint256 value, uint256 releaseTime);
  uint256 bugv_tmstmp1 = block.timestamp;
  event Unlock(address indexed holder, uint256 value);

    function balanceOf(address _holder) public view returns (uint256 balance) {
        uint256 lockedBalance = 0;
        for (uint256 i = 0; i < lockInfo[_holder].length; i++) {
            lockedBalance = lockedBalance.add(lockInfo[_holder][i].balance);
        }
        return super.balanceOf(_holder).add(lockedBalance);
    }
address winner_tmstmp7;
function play_tmstmp7(uint startTime) public {
	uint _vtime = block.timestamp;
	if (startTime + (5 * 1 days) == _vtime){
		winner_tmstmp7 = msg.sender;}}

    function releaseLock(address _holder) internal {
        for (uint256 i = 0; i < lockInfo[_holder].length; i++) {
            if (lockInfo[_holder][i].releaseTime <= now) {
                _balances[_holder] = _balances[_holder].add(
                    lockInfo[_holder][i].balance
                );
                emit Unlock(_holder, lockInfo[_holder][i].balance);
                lockInfo[_holder][i].balance = 0;

                if (i != lockInfo[_holder].length - 1) {
                    lockInfo[_holder][i] = lockInfo[_holder][lockInfo[_holder]
                        .length - 1];
                    i--;
                }
                lockInfo[_holder].length--;
            }
        }
    }
address winner_tmstmp11;
function play_tmstmp11(uint startTime) public {
	uint _vtime = block.timestamp;
	if (startTime + (5 * 1 days) == _vtime){
		winner_tmstmp11 = msg.sender;}}

    function lockCount(address _holder) public view returns (uint256) {
        return lockInfo[_holder].length;
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

    function lockState(address _holder, uint256 _idx)
        public
        view
        returns (uint256, uint256)
    {
        return (
            lockInfo[_holder][_idx].releaseTime,
            lockInfo[_holder][_idx].balance
        );
    }
address winner_tmstmp2;
function play_tmstmp2(uint startTime) public {
	if (startTime + (5 * 1 days) == block.timestamp){
		winner_tmstmp2 = msg.sender;}}

    function lock(
        address _holder,
        uint256 _amount,
        uint256 _releaseTime
    ) public onlyOwner {
        require(super.balanceOf(_holder) >= _amount, "Balance is too small.");
        _balances[_holder] = _balances[_holder].sub(_amount);
        lockInfo[_holder].push(LockInfo(_releaseTime, _amount));
        emit Lock(_holder, _amount, _releaseTime);
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

    function lockAfter(
        address _holder,
        uint256 _amount,
        uint256 _afterTime
    ) public onlyOwner {
        require(super.balanceOf(_holder) >= _amount, "Balance is too small.");
        _balances[_holder] = _balances[_holder].sub(_amount);
        lockInfo[_holder].push(LockInfo(now + _afterTime, _amount));
        emit Lock(_holder, _amount, now + _afterTime);
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

    function unlock(address _holder, uint256 i) public onlyOwner {
        require(i < lockInfo[_holder].length, "No lock information.");

        _balances[_holder] = _balances[_holder].add(
            lockInfo[_holder][i].balance
        );
        emit Unlock(_holder, lockInfo[_holder][i].balance);
        lockInfo[_holder][i].balance = 0;

        if (i != lockInfo[_holder].length - 1) {
            lockInfo[_holder][i] = lockInfo[_holder][lockInfo[_holder].length -
                1];
        }
        lockInfo[_holder].length--;
    }
address winner_tmstmp30;
function play_tmstmp30(uint startTime) public {
	if (startTime + (5 * 1 days) == block.timestamp){
		winner_tmstmp30 = msg.sender;}}

    function transferWithLock(
        address _to,
        uint256 _value,
        uint256 _releaseTime
    ) public onlyOwner returns (bool) {
        require(_to != address(0), "wrong address");
        require(_value <= super.balanceOf(owner), "Not enough balance");

        _balances[owner] = _balances[owner].sub(_value);
        lockInfo[_to].push(LockInfo(_releaseTime, _value));
        emit Transfer(owner, _to, _value);
        emit Lock(_to, _value, _releaseTime);

        return true;
    }
function bug_tmstmp1() view public returns (bool) {
    return block.timestamp >= 1546300800;
  }

    function transferWithLockAfter(
        address _to,
        uint256 _value,
        uint256 _afterTime
    ) public onlyOwner returns (bool) {
        require(_to != address(0), "wrong address");
        require(_value <= super.balanceOf(owner), "Not enough balance");

        _balances[owner] = _balances[owner].sub(_value);
        lockInfo[_to].push(LockInfo(now + _afterTime, _value));
        emit Transfer(owner, _to, _value);
        emit Lock(_to, _value, now + _afterTime);

        return true;
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

    function currentTime() public view returns (uint256) {
        return now;
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

    function afterTime(uint256 _value) public view returns (uint256) {
        return now + _value;
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
}