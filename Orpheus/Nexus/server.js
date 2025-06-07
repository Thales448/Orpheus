

require('dotenv').config();
const express = require('express');
const path = require('path');
const bodyParser = require('body-parser');

const app = express();
const PORT = process.env.PORT || 3000;

// Static GUI
app.use(express.static(path.join(__dirname, 'public')));
app.use('/modules', express.static(path.join(__dirname, 'modules')));
app.use(bodyParser.json());


// Routes
app.use('/', require('./routes/jobs'));
app.use('/k8s', require('./routes/k8s'));
app.use('/db', require('./routes/db')); // optional

// Fallback to index.html


app.listen(PORT, () => {
  console.log(`🚀 Dashboard running at http://localhost:${PORT}`);
});
