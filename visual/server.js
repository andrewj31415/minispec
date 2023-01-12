
console.log("Starting server!");

// see https://nodejs.org/api/http.html
const http = require('http');
const fs = require("fs");

htmlTextFileName = process.argv[2];
console.log(`Serving from file ${htmlTextFileName}`)

htmlText = fs.readFileSync(htmlTextFileName, (err) => {
    if (err) {
        console.error(err);
        console.log("Couldn't open input file");
    }
});

// see https://www.digitalocean.com/community/tutorials/how-to-create-a-web-server-in-node-js-with-the-http-module
const host = 'localhost';
const port = 6191;

const requestListener = function (req, res) {
    res.setHeader("Content-Type", "text/html");
    res.writeHead(200);
    res.end(htmlText);
    console.log("Established connection!")
};

const server = http.createServer(requestListener);
server.listen(port, host, () => {
    console.log(`Server is running on http://${host}:${port}`);
});

// see https://unix.stackexchange.com/questions/30515/how-to-setup-port-redirection-after-a-ssh-connection-has-been-opened
// see https://goteleport.com/blog/ssh-tunneling-explained/

console.log("Finished starting server.");

console.log(`To access the server:
1. Press enter and type "~C" (no quotes) to open a command line inside of ssh.
2. Enter "-L ${port}:127.0.0.1:${port}" (no quotes) to forward the webpage over ssh from athena to your computer.
3. Press the enter key twice.
4. Open "http://localhost:${port}/" (no quotes) in your web browser on your computer`);