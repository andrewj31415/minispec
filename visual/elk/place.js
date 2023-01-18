// to run: node place.js

const fs = require("fs");

const ELK = require("./elk.bundled.js");
const elk = new ELK();

inputJSON = fs.readFileSync(0); // read from stdin into a buffer object

inputJSON = JSON.parse(inputJSON); // convert the buffer object into JSON

elk.layout(inputJSON) // layout the graph
    .then((output) => {
        outputJSON = JSON.stringify(output); // convert elk's json output into a string
        console.log(outputJSON);
    })
    .catch(console.error);
