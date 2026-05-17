#!/usr/bin/env node
// Embed chunks using @xenova/transformers (ONNX, no PyTorch needed)
// Uses multilingual-e5-small for Hebrew + English support
const { pipeline } = require('@xenova/transformers');
const fs = require('fs');

const MODEL = 'Xenova/multilingual-e5-small';  // Supports Hebrew + English

async function main() {
    const chunksPath = process.argv[2];
    const outputPath = process.argv[3] || '/tmp/embeddings.json';
    const isQuery = process.argv.includes('--query');
    
    if (!chunksPath) {
        console.error('Usage: node embed.js <chunks.json> [output.json] [--query]');
        process.exit(1);
    }
    
    console.log(`Loading chunks from ${chunksPath}...`);
    const chunks = JSON.parse(fs.readFileSync(chunksPath, 'utf-8'));
    console.log(`Loaded ${chunks.length} chunks`);
    
    console.log(`Loading embedding model (${MODEL})...`);
    const extractor = await pipeline('feature-extraction', MODEL);
    
    const batchSize = 30; // Smaller batches for multilingual model
    const prefix = isQuery ? 'query: ' : 'passage: ';
    const allEmbeddings = [];
    
    for (let i = 0; i < chunks.length; i += batchSize) {
        const batch = chunks.slice(i, i + batchSize);
        const texts = batch.map(c => prefix + (c.text || c.content || '').trim().slice(0, 400));
        
        const batchNum = Math.floor(i / batchSize) + 1;
        const totalBatches = Math.ceil(chunks.length / batchSize);
        console.log(`Batch ${batchNum}/${totalBatches} (${i + texts.length}/${chunks.length})`);
        
        const output = await extractor(texts, { pooling: 'mean', normalize: true });
        const embeddings = output.tolist();
        
        for (let j = 0; j < batch.length; j++) {
            allEmbeddings.push({
                id: batch[j].id || batch[j].chunk_id || (i + j),
                embedding: embeddings[j],
            });
        }
    }
    
    console.log(`Generated ${allEmbeddings.length} embeddings`);
    fs.writeFileSync(outputPath, JSON.stringify(allEmbeddings));
    console.log(`Saved to ${outputPath}`);
}

main().catch(console.error);
