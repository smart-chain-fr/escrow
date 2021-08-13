#include "TypesEscrow.ligo"
#include "Error.ligo"
#include "State.ligo"

function setAdmin(const admin : address; var s : storage) : return is
block {
    if Tezos.sender = s.admin then s.admin := admin
    else failwith(only_admin);
} with (noOperations, s)


function get_address(const receiver : address) : contract(unit) is
(case (Tezos.get_contract_opt ( receiver) : option(contract(unit))) of
    Some (receiver) -> receiver
    | None -> (failwith (bad_address) : contract (unit))
end);


function initialize_escrow(const params : initialize_escrow_params; var s : storage) : return is
block {
    if Big_map.mem(params.id, s.escrows) then failwith(already_exists)
    else skip;
    if Tezos.amount =/= params.price then failwith(not_right_amount)
    else skip;

    s.escrows[params.id] := record [
        buyer = Tezos.sender;
        seller = params.seller;
        broker = params.broker;
        product = params.product;
        price = params.price;
        comment = map[
            "buyer" -> "";
            "seller" -> ""
        ];
        state = state_initialized;
        time = (None: option (timestamp));
        proof = (None: option (string))
    ]
} with (noOperations, s)


function agree(const id : bytes; var s : storage) : return is
block {
    var esc : escrow := case s.escrows[id] of
        Some(_escrow) -> _escrow
        | None -> failwith(doesnt_exist)
    end;

    if ((Tezos.sender =/= esc.buyer) and (Tezos.sender =/= s.admin)) then failwith(access_denied)
    else skip;
    
    if esc.state =/= state_initialized and 
       esc.state =/= state_buyer_canceled and
       esc.state =/= state_seller_canceled
       then failwith(already_finished)
    else skip;

    if Tezos.sender = s.admin and esc.time =/= (None: option (timestamp)) then
    block {
        var time : timestamp := case esc.time of
            Some (_time) -> _time
            | None -> failwith(no_proof)
        end;
        if Tezos.now - time < 86400 then failwith(too_early)
        else skip;
    }    
    else skip;

    esc.state := state_validated;
    s.escrows[id] := esc;
    const receiver : contract (unit) = get_address(esc.seller);
    const op : operation = Tezos.transaction (unit, esc.price, receiver);
    const ops : list (operation) = list [op]
} with (ops, s)

function receive_item(const params : proof_params; var s : storage) : return is
block {
    if Tezos.sender =/= s.admin then failwith(only_admin)
    else skip;
    var esc : escrow := case s.escrows[params.id] of
        Some(_escrow) -> _escrow
        | None -> failwith(doesnt_exist)
    end;
    esc.proof := params.proof;
    esc.time := Some(Tezos.now);
    s.escrows[params.id] := esc;
} with (noOperations, s)

function cancel_escrow(const id : bytes; var s : storage) : return is
block {
    var esc : escrow := case s.escrows[id] of
        Some(_escrow) -> _escrow
        | None -> failwith(doesnt_exist)
    end;

    if esc.state =/= state_initialized and 
       esc.state =/= state_buyer_canceled and
       esc.state =/= state_seller_canceled
       then failwith(not_cancelable)
    else skip;

    if Tezos.sender = esc.buyer then 
    block {
        if esc.state = state_buyer_canceled then failwith(already_canceled)
        else 
        block {
            if esc.state = state_seller_canceled then esc.state := state_canceled
            else esc.state := state_buyer_canceled
        }
    }
    else skip;


    if Tezos.sender = esc.seller then 
    block {
        if esc.state = state_seller_canceled then failwith(already_canceled)
        else 
        block {
            if esc.state = state_seller_canceled then esc.state := state_canceled
            else esc.state := state_seller_canceled
        }
    }
    else skip;

    s.escrows[id] := esc;
    var ops : list (operation) := list [];

    if esc.state = state_canceled then
    block {
        
        const receiver : contract (unit) = get_address(esc.buyer);
        const op : operation = Tezos.transaction (unit, esc.price, receiver); 
        ops := list [op];    
    }    
    else skip;

}   with(ops, s)
