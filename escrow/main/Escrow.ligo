#include "../partials/MethodEscrow.ligo"

function main (const action : escrowAction; const s : storage) : return is
    case action of
    | SetAdmin(admin) -> setAdmin(admin, s)
    | Initialize_escrow(parameters) -> initialize_escrow(parameters, s)
    end;