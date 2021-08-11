type comments is map(string, string);

type escrow is record [
    buyer : address;
    seller : address;
    broker : option(address);
    product : string;
    price : tez;
    comment : comments;
    state : string;
    time : timestamp
]
type dispute is record [
    buyer : address;
    seller : address;
    price : nat;
    time : timestamp
]

type cancel is record [
    buyer : address;
    seller : address
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
type cancels is big_map(int, cancel);
type return is list (operation) * storage;

const noOperations : list (operation) = nil;

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
