#include "TypesEscrow.ligo"
#include "Error.ligo"

function setAdmin(const admin : address; var s : storage) : return is
block {
    if Tezos.sender = s.admin then s.admin := admin
    else failwith(onlyAdmin);
} with (noOperations, s)


function get_address(const receiver : address) : contract(unit) is
(case (Tezos.get_contract_opt ( receiver) : option(contract(unit))) of
    Some (receiver) -> receiver
    | None -> (failwith (badAddress) : contract (unit))
end);


function initialize_escrow(const params : initialize_escrow_params; var s : storage) : return is
block {
    if Big_map.mem(params.id, s.escrows) then failwith(alreadyExists)
    else skip;
    if Tezos.amount =/= params.price then failwith(notRightAmount)
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
        state = stateInitialized;
        time = Tezos.now
    ]
} with (noOperations, s)


function agree(const id : bytes; var s : storage) : return is
block {
    var esc : escrow := case s.escrows[id] of
        Some(_escrow) -> _escrow
        | None -> failwith(doesntExist)
    end;

    if Tezos.sender =/= esc.buyer then failwith(accessDenied)
    else skip;
    
    esc.state := stateCompleted;
    s.escrows[id] := esc;
    const receiver : contract (unit) = get_address(esc.seller);
    const op : operation = Tezos.transaction (unit, esc.price, receiver);
    const ops : list (operation) = list [op]
} with (ops, s)


function cancel_escrow(const id : bytes; var s : storage) : return is
block {
    var esc : escrow := case s.escrows[id] of
        Some(_escrow) -> _escrow
        | None -> failwith(doesntExist)
    end;

    if not (Tezos.sender = esc.buyer or Tezos.sender = esc.seller) then failwith(accessDenied)
    else skip;

    var cancel : cancel := case s.cancels[id] of
        Some(_cancel) -> _cancel
        | None -> map [ Tezos.sender -> True ]
    end;

    cancel[Tezos.sender] := True;
    
    const buy_cancel : bool = case cancel[esc.buyer] of
        Some(_val) -> _val
        | None -> False
    end;

    const sell_cancel : bool = case cancel[esc.seller] of
        Some(_val) -> _val
        | None -> False
    end;

    s.cancels[id] := cancel;

    var ops : list (operation) := list [];

    if buy_cancel and sell_cancel then
    block {
        const receiver : contract (unit) = get_address(esc.buyer);
        remove id from map s.escrows;
        const op : operation = Tezos.transaction (unit, esc.price, receiver); 
        ops := list [op];    
    }    
    else skip;
}   with(ops, s)
