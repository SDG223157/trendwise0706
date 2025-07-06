// compile-sass.js
const sass = require('sass');
const fs = require('fs');
const path = require('path');

// Define paths
const srcPath = path.join(__dirname, 'app', 'static', 'css', 'scss');
const destPath = path.join(__dirname, 'app', 'static', 'css');

// Create scss directory if it doesn't exist
if (!fs.existsSync(srcPath)) {
    fs.mkdirSync(srcPath, { recursive: true });
}

// Compile function
function compileSass() {
    try {
        const files = fs.readdirSync(srcPath);
        files.forEach(file => {
            if (file.endsWith('.scss')) {
                const inputFile = path.join(srcPath, file);
                const outputFile = path.join(destPath, file.replace('.scss', '.css'));

                sass.render({
                    file: inputFile,
                    outFile: outputFile,
                    outputStyle: 'compressed',
                    sourceMap: true
                }, (error, result) => {
                    if (error) {
                        console.error(`Error compiling ${file}:`, error);
                        return;
                    }

                    // Write CSS file
                    fs.writeFileSync(outputFile, result.css);
                    console.log(`Compiled ${file} -> ${path.basename(outputFile)}`);

                    // Write source map
                    if (result.map) {
                        fs.writeFileSync(`${outputFile}.map`, result.map);
                    }
                });
            }
        });
    } catch (error) {
        console.error('Error reading SCSS files:', error);
    }
}

// Initial compilation
compileSass();

// Watch for changes if --watch flag is provided
if (process.argv.includes('--watch')) {
    console.log('Watching for changes...');
    fs.watch(srcPath, (eventType, filename) => {
        if (filename && filename.endsWith('.scss')) {
            console.log(`Changes detected in ${filename}`);
            compileSass();
        }
    });
}