FROM python:3

ENV DEBIAN_FRONTEND=noninteractive


RUN apt update -y && apt install -y libsodium-dev libsecp256k1-dev libgmp-dev
RUN pip3 install pytezos pytest
RUN wget https://ligolang.org/bin/linux/ligo
RUN chmod +x ./ligo
RUN cp ./ligo /usr/local/bin

COPY escrow escrow

WORKDIR /escrow/main

RUN ligo compile-contract Escrow.ligo main > Escrow.tz  

ENTRYPOINT [ "pytest"]