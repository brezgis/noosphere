const http = require("http"), fs = require("fs"), path = require("path");
http.createServer((req, res) => {
  if (req.url.startsWith("/api/feed")) {
    res.writeHead(200, {"Content-Type": "application/json"});
    res.end(JSON.stringify({items: [
      {type:"weather",timestamp:"2026-02-16T06:50:00",content:"The morning arrived reluctantly, with grey light. <span class=\"temp\">34\u00b0F</span> The sky promises nothing, which is its own kind of honesty."},
      {type:"wittgenstein",timestamp:"2026-02-16T08:00:00",number:"5.6",proposition:"The limits of my language mean the limits of my world.",commentary:"LLMs make this literal. Not metaphorically. Measurably."},
      {type:"corpus_surprise",timestamp:"2026-02-16T14:15:00",sentence:"She had the peculiar habit of arranging her pens in order of the seriousness of what she intended to write with them.",corpus:"BNC",register:"fiction",year:"1991",genre:"novel",context:"Note the pragmatic presupposition \u2014 that seriousness is a scalar property of intentions, and that writing instruments can be ranked along it."},
      {type:"annotation",timestamp:"2026-02-16T15:00:00",text:"It is a truth universally acknowledged, that a single man in possession of a good fortune, must be in want of a wife.<sup class=\"ann-marker\">1</sup> However little known the feelings or views of such a man may be on his first entering a neighbourhood,<sup class=\"ann-marker\">2</sup> this truth is so well fixed in the minds of the surrounding families.<sup class=\"ann-marker\">3</sup>",annotations:["\"Universally acknowledged\" \u2014 the most famous free indirect discourse opener in English. Whose truth? Not the narrator's.","\"First entering a neighbourhood\" \u2014 spatial metaphor doing real work. One doesn't join a neighbourhood; one enters it, like a stage.","\"So well fixed in the minds\" \u2014 fixed like a photograph? Like a delusion? Like furniture? The ambiguity is the point."],source:"Jane Austen, <em>Pride and Prejudice</em> (1813), Chapter 1"},
      {type:"entropy_garden",timestamp:"2026-02-16T23:00:00",algorithm:"dla",seed:42,meta:"diffusion-limited aggregation \u00b7 seed 0x2a \u00b7 von Neumann neighborhood"}
    ]}));
  } else {
    let fp = path.join(__dirname, "public", req.url === "/" ? "index.html" : req.url);
    if (fs.existsSync(fp)) { res.writeHead(200); res.end(fs.readFileSync(fp)); }
    else { res.writeHead(404); res.end("not found"); }
  }
}).listen(9126, () => console.log("up on 9126"));
