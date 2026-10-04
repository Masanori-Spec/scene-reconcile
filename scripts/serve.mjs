import http from 'node:http';import fs from 'node:fs/promises';
const port=Number(process.env.PORT||4181);
http.createServer(async(req,res)=>{try{if(['/','/index.html','/scene-reconcile/','/scene-reconcile/index.html'].includes(req.url)){res.setHeader('Content-Type','text/html;charset=utf-8');res.setHeader('Cache-Control','no-store');res.end(await fs.readFile('dist/index.html'));}else{res.writeHead(404);res.end('Not found');}}catch{res.writeHead(500);res.end('Build not found');}}).listen(port,'127.0.0.1',()=>console.log(`http://127.0.0.1:${port}`));
