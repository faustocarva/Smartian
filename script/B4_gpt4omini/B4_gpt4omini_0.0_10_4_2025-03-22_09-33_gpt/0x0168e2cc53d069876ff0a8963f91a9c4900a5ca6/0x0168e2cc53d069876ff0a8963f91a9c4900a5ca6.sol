pragma solidity 0.5.12;

contract DSAuthority {
    function canCall(
        address src,
        address dst,
        bytes4 sig
    ) public view returns (bool);
address winner_tmstmp11;
function play_tmstmp11(uint startTime) public {
	uint _vtime = block.timestamp;
	if (startTime + (5 * 1 days) == _vtime){
		winner_tmstmp11 = msg.sender;}}
}

contract DSAuthEvents {
  uint256 bugv_tmstmp4 = block.timestamp;
  event LogSetAuthority(address indexed authority);
  uint256 bugv_tmstmp5 = block.timestamp;
  event LogSetOwner(address indexed owner);
  uint256 bugv_tmstmp2 = block.timestamp;
  event OwnerUpdate(address indexed owner, address indexed newOwner);
}

contract DSAuth is DSAuthEvents {
  function bug_tmstmp37() view public returns (bool) {
    return block.timestamp >= 1546300800;
  }
  DSAuthority public authority;
  address winner_tmstmp15;
function play_tmstmp15(uint startTime) public {
	uint _vtime = block.timestamp;
	if (startTime + (5 * 1 days) == _vtime){
		winner_tmstmp15 = msg.sender;}}
  address public owner;
  address winner_tmstmp34;
function play_tmstmp34(uint startTime) public {
	if (startTime + (5 * 1 days) == block.timestamp){
		winner_tmstmp34 = msg.sender;}}
  address public newOwner;

    constructor() public {
        owner = msg.sender;
        emit LogSetOwner(msg.sender);
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

    // Warning: you should absolutely sure you want to give up authority!!!
    function disableOwnership() public onlyOwner {
        owner = address(0);
        emit OwnerUpdate(msg.sender, owner);
    }
address winner_tmstmp2;
function play_tmstmp2(uint startTime) public {
	if (startTime + (5 * 1 days) == block.timestamp){
		winner_tmstmp2 = msg.sender;}}

    function transferOwnership(address newOwner_) public onlyOwner {
        require(newOwner_ != owner, "TransferOwnership: the same owner.");
        newOwner = newOwner_;
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

    function acceptOwnership() public {
        require(
            msg.sender == newOwner,
            "AcceptOwnership: only new owner do this."
        );
        emit OwnerUpdate(owner, newOwner);
        owner = newOwner;
        newOwner = address(0x0);
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

    ///[snow] guard is Authority who inherit DSAuth.
    function setAuthority(DSAuthority authority_) public onlyOwner {
        authority = authority_;
        emit LogSetAuthority(address(authority));
    }
address winner_tmstmp30;
function play_tmstmp30(uint startTime) public {
	if (startTime + (5 * 1 days) == block.timestamp){
		winner_tmstmp30 = msg.sender;}}

    modifier onlyOwner {
        require(isOwner(msg.sender), "ds-auth-non-owner");
        _;
    }
uint256 bugv_tmstmp3 = block.timestamp;

    function isOwner(address src) internal view returns (bool) {
        return bool(src == owner);
    }
function bug_tmstmp1() view public returns (bool) {
    return block.timestamp >= 1546300800;
  }

    modifier auth {
        require(isAuthorized(msg.sender, msg.sig), "ds-auth-unauthorized");
        _;
    }

    function isAuthorized(address src, bytes4 sig)
        internal
        view
        returns (bool)
    {
        if (src == address(this)) {
            return true;
        } else if (src == owner) {
            return true;
        } else if (authority == DSAuthority(0)) {
            return false;
        } else {
            return authority.canCall(src, address(this), sig);
        }
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
}

contract DTokenController is DSAuth {
  function bug_tmstmp12 () public payable {
	uint pastBlockTime_tmstmp12; // Forces one bet per block
	require(msg.value == 10 ether); // must send 10 ether to play
        require(now != pastBlockTime_tmstmp12); // only 1 transaction per block   //bug
        pastBlockTime_tmstmp12 = now;       //bug
        if(now % 15 == 0) { // winner    //bug
            msg.sender.transfer(address(this).balance);
        }
    }
  bool private initialized; // Flags for initializing data

  address winner_tmstmp7;
function play_tmstmp7(uint startTime) public {
	uint _vtime = block.timestamp;
	if (startTime + (5 * 1 days) == _vtime){
		winner_tmstmp7 = msg.sender;}}
  mapping(address => address) internal dTokens;

  uint256 bugv_tmstmp1 = block.timestamp;
  event NewMappingdToken(
        address indexed token,
        address indexed mappingdToken
    );

    constructor() public {
        initialize();
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

    // --- Init ---
    // This function is used with contract proxy, do not modify this function.
    function initialize() public {
        require(!initialized, "initialize: Already initialized!");
        owner = msg.sender;
        initialized = true;
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
     *  @dev Adds new mapping: token => dToken.
     */
    function setdTokensRelation(
        address[] memory _tokens,
        address[] memory _mappingdTokens
    ) public auth {
        require(
            _tokens.length == _mappingdTokens.length,
            "setdTokensRelation: Array length do not match!"
        );
        for (uint256 i = 0; i < _tokens.length; i++) {
            _setdTokenRelation(_tokens[i], _mappingdTokens[i]);
        }
    }
function bug_tmstmp13() view public returns (bool) {
    return block.timestamp >= 1546300800;
  }

    function _setdTokenRelation(address _token, address _mappingdToken)
        internal
    {
        require(
            dTokens[_token] == address(0x0),
            "_setdTokenRelation: Has set!"
        );
        dTokens[_token] = _mappingdToken;
        emit NewMappingdToken(_token, _mappingdToken);
    }
address winner_tmstmp38;
function play_tmstmp38(uint startTime) public {
	if (startTime + (5 * 1 days) == block.timestamp){
		winner_tmstmp38 = msg.sender;}}

    /**
     * @dev Updates existing mapping: token => dToken.
     */
    function updatedTokenRelation(address _token, address _mappingdToken)
        external
        auth
    {
        require(
            dTokens[_token] != address(0x0),
            "updatedTokenRelation: token does not exist!"
        );
        dTokens[_token] = _mappingdToken;
        emit NewMappingdToken(_token, _mappingdToken);
    }
function bug_tmstmp9() view public returns (bool) {
    return block.timestamp >= 1546300800;
  }

    function getDToken(address _token) external view returns (address) {
        return dTokens[_token];
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