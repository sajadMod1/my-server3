const express = require('express');
const crypto = require('crypto');
const app = express();

const SECRET_KEY = process.env.SECRET_KEY;
const IV = process.env.IV;

function encrypt(text) {
    const cipher = crypto.createCipheriv(
        'aes-256-cbc',
        Buffer.from(SECRET_KEY),
        Buffer.from(IV)
    );
    let encrypted = cipher.update(text, 'utf8', 'base64');
    encrypted += cipher.final('base64');
    return encrypted;
}


app.get('/bypass', async (req, res) => {
    try {
        const response = await fetch(process.env.BYPASS_URL);
        const data = await response.text();
        res.send(encrypt(data));
    } catch (err) {
        res.status(500).json({ error: 'Failed' });
    }
});


app.get('/download', async (req, res) => {
    try {
        const url = process.env.DOWNLOAD_URL;
        res.send(encrypt(url));
    } catch (err) {
        res.status(500).json({ error: 'Failed' });
    }
});

module.exports = app;