// to run: node place.js

const ELK = require("./elk.bundled.js");
const elk = new ELK();

const graph = {
    id: "root",
    layoutOptions: { "elk.algorithm": "layered" },
    children: [
        { id: "n1", width: 30, height: 30 },
        { id: "n2", width: 30, height: 30 },
        { id: "n3", width: 30, height: 30 },
    ],
    edges: [
        { id: "e1", sources: ["n1"], targets: ["n2"] },
        { id: "e2", sources: ["n1"], targets: ["n3"] },
    ],
};

// See https://nodejs.org/en/knowledge/command-line/how-to-parse-command-line-arguments/
console.log(process.argv);

elk.layout(graph)
    .then((output) => {
        console.log(output);
        console.log(JSON.stringify(output));
    })
    .catch(console.error);
