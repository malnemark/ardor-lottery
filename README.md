# ardor-lottery
A simple Python script to run a lottery on a local Ardor node.

It will send three random assets of the provided list of choices. The buyer of a lottery ticket needs to add a message (currently "lottery") to its transactions. The lottery uses Ignis coins.


To run your lottery, create a configuration file (e.g. `config.json`) in the ardor-lotter folder.

```
{
  "nodeurl":"http://localhost:26876/nxt",
  "account":"ARDOR-SOME-ACCOU-NT",
  "passphrase":"many secret words",
  "assets":["assetid1","assetid2","assetid3"]
}
```
And then start the lottery

```
./lottery.py config.json
```
