type comments is map(string, string);

type escrow is record [
    buyer : address;
    seller : address;
    broker : option(address);
    product : string;
    price : tez;
    comment : comments;
    state : string;
    time : option(timestamp);
    proof : option(string);
]

type proof_params is record [
    id : bytes;
    proof : string
]

type dispute is record [
    buyer : address;
    seller : address;
    price : nat;
    time : timestamp
]

type initialize_escrow_params is record [
    seller : address;
    broker : option(address);
    product : string;
    price : tez;
    id : bytes
]

type disputes is big_map(int, dispute);
type escrows is big_map(bytes, escrow);
type judges is big_map(nat, address);
type judge_reward is big_map(string, nat);

const noOperations : list (operation) = nil;

const notEnoughTez : string = "Not enough XTZ to initialize escrow";
type storage is record [
    escrows : escrows;
    disputes : disputes;
    judges : judges;
    judge_reward : judge_reward;
    admin : address;
    voting_contract : option(address);
    payment_contract : option(address);
]

type return is list (operation) * storage;

type escrowAction is
| Agree of (bytes)
| Initialize_escrow of initialize_escrow_params
| SetAdmin of (address)
| Cancel_escrow of (bytes)
| Receive_item of (proof_params)
