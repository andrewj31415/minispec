// to run: node place.js

const fs = require("fs");

const ELK = require("./elk.bundled.js");
const elk = new ELK();

inputJSON = fs.readFileSync("./visualDir/elkInput.txt", (err) => {
    if (err) {
        console.error(err);
        console.log("Couldn't open input file");
    }
}); // read from the input file into a buffer object

inputJSON = JSON.parse(inputJSON); // convert the buffer object into JSON

fs.writeFileSync("./visualDir/elkOutput.txt", ""); // clear the output in case an error occurs when layouting

elk.layout(inputJSON) // layout the graph
    .then((output) => {
        outputJSON = JSON.stringify(output); // convert elk's json output into a string
        fs.writeFile("./visualDir/elkOutput.txt", outputJSON, (err) => {
            // put the output string into the output file
            if (err) {
                console.error(err);
                console.log("Couldn't open output file");
            }
        });
    })
    .catch(console.error);
