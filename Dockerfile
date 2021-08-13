FROM smartnodefr/pythonligo:3.22

COPY escrow escrow

WORKDIR /escrow/main

RUN ligo compile-contract Escrow.ligo main > Escrow.tz  

ENTRYPOINT [ "pytest"]