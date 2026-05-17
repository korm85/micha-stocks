#!/usr/bin/env node
// Embed chunks using @xenova/transformers with configurable model
// Usage: node embed_better.js <chunks.json> [output.json] [--model MODEL_NAME] [--query]
const { pipeline } = require('@xenova/transformers');
const fs = require('fs');

async function main() {
    const chunksPath = process.argv[2];
    const outputPath = process.argv[3] || '/tmp/embeddings.json';
    const isQuery = process.argv.includes('--query');
    
    // Extract model name from --model flag, or default to multilingual-e5-small
    let modelIdx = process.argv.indexOf('--model');
    const MODEL = modelIdx >= 0 ? process.argv[modelIdx + 1] : 'Xenova/multilingual-e5-small';
    
    if (!chunksPath) {
        console.error('Usage: node embed_better.js <chunks.json> [output.json] [--model MODEL] [--query]');
        process.exit(1);
    }
    
    console.log(`Loading chunks from ${chunksPath}...`);
    const chunks = JSON.parse(fs.readFileSync(chunksPath, 'utf-8'));
    console.log(`Loaded ${chunks.length} chunks`);
    
    console.log(`Loading embedding model (${MODEL})...`);
    const extractor = await pipeline('feature-extraction', MODEL);
    
    const batchSize = 30;
    
    // Different models have different prefix conventions
    let passagePrefix = '';
    let queryPrefix = '';
    
    if (MODEL.includes('multilingual-e5') || MODEL.includes('e5-small') || MODEL.includes('e5-base') || MODEL.includes('e5-large')) {
        // E5 models use 'passage: ' and 'query: ' prefixes
        passagePrefix = 'passage: ';
        queryPrefix = 'query: ';
    } else if (MODEL.includes('bge-small') || MODEL.includes('bge-base') || MODEL.includes('bge-large')) {
        // BGE models: use instruction for query, nothing for passages
        passagePrefix = '';
        queryPrefix = 'Represent this sentence for searching relevant passages: ';
    } else {
        // MiniLM and others: no prefix needed
        passagePrefix = '';
        queryPrefix = '';
    }
    
    const prefix = isQuery ? queryPrefix : passagePrefix;
    
    console.log(`Using ${isQuery ? 'query' : 'passage'} prefix: "${prefix}"`);
    
    const allEmbeddings = [];
    
    for (let i = 0; i < chunks.length; i += batchSize) {
        const batch = chunks.slice(i, i + batchSize);
        const texts = batch.map(c => prefix + (c.text || c.content || '').trim().slice(0, 500));
        
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
