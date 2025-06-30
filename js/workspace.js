// Get database name from URL parameters
const urlParams = new URLSearchParams(window.location.search);
const dbName = urlParams.get('db');

// Store schema data globally for future use
let databaseSchema = null;
let databaseType = null; // Store database type globally

// Function to fetch database type from backend
function fetchDatabaseType() {
    if (!dbName) {
        console.error('No database name provided');
        return Promise.resolve(null);
    }

    return fetch(`http://127.0.0.1:5501/get-database-type?db_name=${encodeURIComponent(dbName)}`)
        .then(response => {
            if (!response.ok) {
                console.warn(`Database type endpoint returned ${response.status}, will detect from schema`);
                return null; // Return null to trigger fallback detection
            }
            return response.json();
        })
        .then(data => {
            if (data && data.error) {
                console.error('Error fetching database type:', data.error);
                return null;
            }
            if (data && data.db_type) {
                console.log('Database type fetched:', data.db_type);
                return data.db_type;
            }
            return null;
        })
        .catch(error => {
            console.error('Error fetching database type:', error);
            console.log('Will use fallback database type detection');
            return null;
        });
}

// Function to detect database type from schema (fallback)
function detectDatabaseTypeFromSchema(schema) {
    if (!schema || !Array.isArray(schema)) {
        return 'mysql'; // Default fallback
    }
    
    // Check if schema has MongoDB-like characteristics
    for (let table of schema) {
        if (table.columns) {
            for (let column of table.columns) {
                // If we see ObjectId or MongoDB-specific types, it's likely MongoDB
                if (column.type && (
                    column.type.toLowerCase().includes('objectid') ||
                    column.type.toLowerCase().includes('mongodb') ||
                    column.type.toLowerCase() === 'bson'
                )) {
                    console.log('Detected MongoDB from schema (ObjectId field)');
                    return 'mongodb';
                }
            }
        }
    }
    
    // Check if table names suggest MongoDB collections
    for (let table of schema) {
        if (table.table_name && (
            table.table_name.toLowerCase().includes('collection') ||
            table.table_name.toLowerCase().includes('document')
        )) {
            console.log('Detected MongoDB from schema (collection-like name)');
            return 'mongodb';
        }
    }
    
    console.log('Detected SQL database from schema');
    return 'mysql';
}

// Function to update UI based on database type
function updateUIForDatabaseType(dbType) {
    const sqlInput = document.getElementById('sqlInput');
    
    if (dbType && dbType.toLowerCase() === 'mongodb') {
        // Update SQL input placeholder for MongoDB
        if (sqlInput) {
            sqlInput.placeholder = "Enter MongoDB query (e.g., db.customers.find() or db.products.find({price: {$gt: 100}}))";
        }
        
        console.log('UI updated for MongoDB workspace');
    } else {
        // Update SQL input placeholder for SQL databases
        if (sqlInput) {
            sqlInput.placeholder = "Enter SQL query (e.g., SELECT * FROM users WHERE age > 25)";
        }
        
        console.log('UI updated for SQL workspace');
    }
}

// Function to load database schema
function loadSchema() {
    if (!dbName) {
        console.error('No database name provided');
        document.getElementById('schemaContent').innerHTML = '<div style="color: #ff6b6b;">No database selected</div>';
        return;
    }

    const schemaContent = document.getElementById('schemaContent');
    schemaContent.innerHTML = 'Loading schema...';

    // Set the database name label
    document.getElementById('dbNameLabel').textContent = `Database: ${dbName}`;

    console.log('Fetching schema for database:', dbName);

    // Fetch schema from backend
    fetch(`http://127.0.0.1:5501/get-schema?db_name=${encodeURIComponent(dbName)}`)
        .then(response => {
            console.log('Schema response status:', response.status);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(schema => {
            console.log('Received schema:', schema);
            
            if (!schema || !Array.isArray(schema)) {
                throw new Error('Invalid schema format received from server');
            }

            // Store schema in localStorage for future use
            localStorage.setItem(`schema_${dbName}`, JSON.stringify(schema));
            
            // Display schema in the panel
            let schemaHtml = '';
            schema.forEach((table, idx) => {
                if (!table.table_name || !Array.isArray(table.columns)) {
                    console.warn('Invalid table format:', table);
                    return;
                }

                // Each table gets a dropdown button and a hidden attribute list
                const tableId = `table-attr-${idx}`;
                schemaHtml += `<div class="table-info table-item">`;
                schemaHtml += `<div style="display: flex; align-items: center; justify-content: space-between; cursor: pointer;" onclick="toggleAttributes('${tableId}')">`;
                schemaHtml += `<span class="table-name">${table.table_name}</span>`;
                schemaHtml += `<button class="dropdown-btn" style="background: none; border: none; color: #a084ee; font-size: 1.1em; cursor: pointer; margin-left: 8px;" tabindex="-1"><i class="fas fa-chevron-down" id="icon-${tableId}"></i></button>`;
                schemaHtml += `</div>`;
                schemaHtml += `<ul class="attribute-list" id="${tableId}" style="display: none; margin-top: 8px;">`;
                table.columns.forEach(column => {
                    if (!column.name || !column.type) {
                        console.warn('Invalid column format:', column);
                        return;
                    }
                    schemaHtml += `<li class="attribute-item">${column.name} <span class="attribute-type">(${column.type})</span></li>`;
                });
                schemaHtml += `</ul>`;
                schemaHtml += `</div>`;
            });
            
            if (schemaHtml === '') {
                schemaHtml = '<div style="color: #ff6b6b;">No tables found in the database</div>';
            }
            
            schemaContent.innerHTML = schemaHtml;

            // Add dropdown toggle logic
            window.toggleAttributes = function(attrId) {
                const ul = document.getElementById(attrId);
                const icon = document.getElementById('icon-' + attrId);
                if (ul) {
                    if (ul.style.display === 'none') {
                        ul.style.display = 'block';
                        if (icon) icon.classList.remove('fa-chevron-down'), icon.classList.add('fa-chevron-up');
                    } else {
                        ul.style.display = 'none';
                        if (icon) icon.classList.remove('fa-chevron-up'), icon.classList.add('fa-chevron-down');
                    }
                }
            };
        })
        .catch(error => {
            console.error('Error loading schema:', error);
            schemaContent.innerHTML = `<div style="color: #ff6b6b;">Error loading schema: ${error.message}</div>`;
            // Clear any existing schema from localStorage
            localStorage.removeItem(`schema_${dbName}`);
        });
}

// Load schema when page loads
document.addEventListener('DOMContentLoaded', function() {
    loadSchema();
    
    // Fetch database type and update UI
    if (dbName) {
        // First try to get from localStorage (for faster loading)
        const selectedDB = JSON.parse(localStorage.getItem('selectedDB'));
        if (selectedDB && selectedDB.db_name === dbName) {
            databaseType = selectedDB.db_type;
            updateUIForDatabaseType(databaseType);
        }
        
        // Always fetch from backend to ensure accuracy, with fallback
        fetchDatabaseType().then(dbType => {
            if (dbType) {
                databaseType = dbType;
                updateUIForDatabaseType(dbType);
                // Update localStorage with the fetched database info
                const dbInfo = {
                    db_name: dbName,
                    db_type: dbType
                };
                localStorage.setItem('selectedDB', JSON.stringify(dbInfo));
            } else {
                // Fallback: detect from schema
                const schema = JSON.parse(localStorage.getItem(`schema_${dbName}`));
                if (schema) {
                    const fallbackDbType = detectDatabaseTypeFromSchema(schema);
                    databaseType = fallbackDbType;
                    updateUIForDatabaseType(fallbackDbType);
                    console.log('Using fallback database type detection on page load:', fallbackDbType);
                    
                    // Update localStorage with the detected database info
                    const dbInfo = {
                        db_name: dbName,
                        db_type: fallbackDbType
                    };
                    localStorage.setItem('selectedDB', JSON.stringify(dbInfo));
                }
            }
        });
    }

    // Remove the SQL to MongoDB button from the DOM if it exists
    const sqlToMongoBtn = document.getElementById('sqlToMongoBtn');
    if (sqlToMongoBtn) {
        sqlToMongoBtn.parentNode.removeChild(sqlToMongoBtn);
    }
});

// Function to execute SQL query
function runQuery() {
    const query = document.getElementById('sqlInput').value.trim();
    if (!query) {
        alert('Please enter a query');
        return;
    }

    // Get user data from localStorage
    const user = JSON.parse(localStorage.getItem('user'));
    const user_id = user ? user.user_id : null;

    console.log('Running query:', query);
    console.log('Database name:', dbName);
    console.log('User ID:', user_id);
    console.log('Database type:', databaseType);

    const outputBox = document.getElementById('outputBox');
    outputBox.innerHTML = '<div style="color: #682bd7; padding: 10px;">Executing query...</div>';
    
    console.log('Executing query for user_id:', user_id);

    // Execute query
    fetch('http://127.0.0.1:5501/execute-query', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            dbName: dbName,
            query: query,
            user_id: user_id  // Include user_id in the request
        })
    })
    .then(response => {
        if (!response.ok) {
            // Handle 403 errors specially for blocked operations
            if (response.status === 403) {
                return response.json().then(data => {
                    throw new Error(`BLOCKED_OPERATION: ${data.error || 'Operation blocked'}`);
                });
            }
            // For other errors, try to get the error message from the response
            return response.json().then(data => {
                console.log('Error response data:', data);
                throw new Error(`HTTP ${response.status}: ${data.error || 'Unknown error'}`);
            }).catch(parseError => {
                console.log('Could not parse error response:', parseError);
                // If we can't parse the JSON, just throw the status error
                throw new Error(`HTTP error! status: ${response.status}`);
            });
        }
        return response.json();
    })
    .then(data => {
        if (data.error) {
            // Special handling for cloud database modification blocking
            if (data.blocked_operation) {
                outputBox.innerHTML = `<div style="color: #e74c3c; padding: 15px; background: #fdf2f2; border-radius: 8px; border-left: 4px solid #e74c3c; font-weight: bold;">
                    <div style="font-size: 1.1em; margin-bottom: 8px;">🚫 Cloud Database Protection</div>
                    <div>${data.error}</div>
                    <div style="margin-top: 10px; font-size: 0.9em; color: #666;">
                        Only SELECT queries are allowed for cloud databases to protect your data.
                    </div>
                </div>`;
            } else {
                outputBox.innerHTML = `<div style="color: #ff6b6b; padding: 10px; background: #fff5f5; border-radius: 4px;">${data.error}</div>`;
            }
        } else {
            let resultHtml = '';
            
            // Add operation message if available
            if (data.message) {
                resultHtml += `<div style="color: #28a745; padding: 10px; background: #f8fff9; border-radius: 4px; margin-bottom: 10px; border-left: 4px solid #28a745;">
                    <strong>${data.operation ? data.operation.toUpperCase() : 'SUCCESS'}:</strong> ${data.message}
                </div>`;
            }
            
            // Handle different operation types
            if (data.operation === 'select' || (data.columns && data.rows)) {
                // Display results in a table format for SELECT queries
                resultHtml += '<div style="overflow-x: auto;">';
                resultHtml += '<table style="width: 100%; border-collapse: collapse; margin-top: 10px;">';
                
                // Add header row
                if (data.columns && data.columns.length > 0) {
                    resultHtml += '<tr>';
                    data.columns.forEach(column => {
                        resultHtml += `<th style="padding: 12px; border: 1px solid #682bd7; text-align: left; background: #f8f5ff;">${column}</th>`;
                    });
                    resultHtml += '</tr>';
                }
                
                // Add data rows - FIXED: Use column order to map values correctly
                if (data.rows && data.rows.length > 0) {
                    data.rows.forEach(row => {
                        resultHtml += '<tr>';
                        // Use the column order to ensure correct mapping
                        data.columns.forEach(column => {
                            const value = row[column];
                            resultHtml += `<td style="padding: 12px; border: 1px solid #682bd7;">${value !== null && value !== undefined ? value : '<em>NULL</em>'}</td>`;
                        });
                        resultHtml += '</tr>';
                    });
                } else {
                    resultHtml += '<tr><td colspan="' + (data.columns ? data.columns.length : 1) + '" style="text-align: center; padding: 20px;">No results found</td></tr>';
                }
                
                resultHtml += '</table></div>';
                
                // Add result summary
                const rowCount = data.rows ? data.rows.length : 0;
                const columnCount = data.columns ? data.columns.length : 0;
                resultHtml += `<div style="margin-top: 10px; color: #666; font-size: 0.9em;">
                    Found ${rowCount} row${rowCount !== 1 ? 's' : ''} with ${columnCount} column${columnCount !== 1 ? 's' : ''}
                </div>`;
                
            } else if (data.operation === 'insert' || data.operation === 'update' || data.operation === 'delete') {
                // Show affected rows for DML operations
                if (data.rows && data.rows.length > 0) {
                    resultHtml += '<div style="overflow-x: auto;">';
                    resultHtml += '<table style="width: 100%; border-collapse: collapse; margin-top: 10px;">';
                    
                    // Add header row
                    if (data.columns && data.columns.length > 0) {
                        resultHtml += '<tr>';
                        data.columns.forEach(column => {
                            resultHtml += `<th style="padding: 12px; border: 1px solid #682bd7; text-align: left; background: #f8f5ff;">${column}</th>`;
                        });
                        resultHtml += '</tr>';
                    }
                    
                    // Add data rows - FIXED: Use column order to map values correctly
                    data.rows.forEach(row => {
                        resultHtml += '<tr>';
                        // Use the column order to ensure correct mapping
                        data.columns.forEach(column => {
                            const value = row[column];
                            resultHtml += `<td style="padding: 12px; border: 1px solid #682bd7;">${value !== null && value !== undefined ? value : '<em>NULL</em>'}</td>`;
                        });
                        resultHtml += '</tr>';
                    });
                    
                    resultHtml += '</table></div>';
                }
                
            } else if (data.operation === 'create' || data.operation === 'alter' || data.operation === 'drop' || data.operation === 'truncate') {
                // Show success message for DDL operations
                resultHtml += `<div style="color: #28a745; padding: 15px; background: #f8fff9; border-radius: 4px; border-left: 4px solid #28a745;">
                    <strong>✓ ${data.operation.toUpperCase()} Operation Completed Successfully</strong><br>
                    ${data.message || 'The operation was executed without errors.'}
                </div>`;
                
            } else {
                // Fallback for other operations
                if (data.rows && data.rows.length > 0) {
                    resultHtml += '<div style="overflow-x: auto;">';
                    resultHtml += '<table style="width: 100%; border-collapse: collapse; margin-top: 10px;">';
                    
                    // Add header row
                    if (data.columns && data.columns.length > 0) {
                        resultHtml += '<tr>';
                        data.columns.forEach(column => {
                            resultHtml += `<th style="padding: 12px; border: 1px solid #682bd7; text-align: left; background: #f8f5ff;">${column}</th>`;
                        });
                        resultHtml += '</tr>';
                    }
                    
                    // Add data rows - FIXED: Use column order to map values correctly
                    data.rows.forEach(row => {
                        resultHtml += '<tr>';
                        // Use the column order to ensure correct mapping
                        data.columns.forEach(column => {
                            const value = row[column];
                            resultHtml += `<td style="padding: 12px; border: 1px solid #682bd7;">${value !== null && value !== undefined ? value : '<em>NULL</em>'}</td>`;
                        });
                        resultHtml += '</tr>';
                    });
                    
                    resultHtml += '</table></div>';
                }
            }
            
            outputBox.innerHTML = resultHtml;
        }
    })
    .catch(error => {
        console.error('Error executing query:', error);
        
        // Check if this is a blocked operation error
        if (error.message && error.message.startsWith('BLOCKED_OPERATION:')) {
            const blockedMessage = error.message.replace('BLOCKED_OPERATION: ', '');
            outputBox.innerHTML = `<div style="color: #e74c3c; padding: 15px; background: #fdf2f2; border-radius: 8px; border-left: 4px solid #e74c3c; font-weight: bold;">
                <div style="font-size: 1.1em; margin-bottom: 8px;">🚫 Cloud Database Protection</div>
                <div>${blockedMessage}</div>
                <div style="margin-top: 10px; font-size: 0.9em; color: #666;">
                    Only SELECT queries are allowed for cloud databases to protect your data.
                </div>
            </div>`;
        } else {
            outputBox.innerHTML = `<div style="color: #ff6b6b; padding: 10px; background: #fff5f5; border-radius: 4px;">Error: ${error.message}</div>`;
        }
    });
}

// Function to convert English to Query (SQL or MongoDB)
function convertToSQL() {
    const englishQuery = document.getElementById('nlInput').value;
    if (!englishQuery) {
        alert('Please enter your question in English');
        return;
    }

    // Get schema from localStorage
    const schema = JSON.parse(localStorage.getItem(`schema_${dbName}`));
    if (!schema) {
        alert('Database schema not found. Please try refreshing the page.');
        return;
    }

    // Use global database type or fallback to schema detection
    let dbType = databaseType;
    if (!dbType) {
        const selectedDB = JSON.parse(localStorage.getItem('selectedDB'));
        if (selectedDB && selectedDB.db_type) {
            dbType = selectedDB.db_type;
        } else {
            // Fallback: detect from schema
            dbType = detectDatabaseTypeFromSchema(schema);
            console.log('Using fallback database type detection:', dbType);
        }
    }

    console.log('Converting to query for database type:', dbType);

    // Show loading state
    const sqlInput = document.getElementById('sqlInput');
    sqlInput.value = 'Converting...';

    // Send to backend for conversion
    fetch('http://127.0.0.1:5501/convert-to-sql', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            prompt: englishQuery,
            dbName: dbName,
            schema: schema
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.error) {
            sqlInput.value = `-- Error: ${data.error}`;
        } else {
            // Handle the response - backend returns 'query' property
            let generatedQuery = '';
            if (data.query) {
                generatedQuery = data.query;
            } else if (data.sql) {
                generatedQuery = data.sql;
            } else if (data.mongodb) {
                generatedQuery = data.mongodb;
            } else {
                sqlInput.value = `-- Error: No query generated`;
                return;
            }

            // Clean up the query (remove any markdown code blocks if present)
            if (generatedQuery.startsWith('```sql')) {
                generatedQuery = generatedQuery.replace('```sql', '').replace('```', '').trim();
            } else if (generatedQuery.startsWith('```javascript')) {
                generatedQuery = generatedQuery.replace('```javascript', '').replace('```', '').trim();
            } else if (generatedQuery.startsWith('```')) {
                generatedQuery = generatedQuery.replace('```', '').trim();
            }
            
            sqlInput.value = generatedQuery;
        }
    })
    .catch(error => {
        console.error('Error converting to query:', error);
        sqlInput.value = `-- Error: ${error.message}`;
    });
}

// Function to convert SQL to English
function convertToNL() {
    const sqlQuery = document.getElementById('sqlInput').value;
    if (!sqlQuery) {
        alert('Please enter a SQL query');
        return;
    }

    // Get schema from localStorage
    const schema = JSON.parse(localStorage.getItem(`schema_${dbName}`));
    if (!schema) {
        alert('Database schema not found. Please try refreshing the page.');
        return;
    }

    console.log('Converting SQL to English:', {
        sqlQuery,
        dbName,
        schema
    });

    // Show loading state
    const nlInput = document.getElementById('nlInput');
    nlInput.value = 'Converting...';

    // Send to backend for conversion
    fetch('http://127.0.0.1:5501/convert-to-english', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            prompt: sqlQuery,
            dbName: dbName,
            schema: schema
        })
    })
    .then(response => {
        console.log('Response status:', response.status);
        if (!response.ok) {
            // Handle 403 errors specially for blocked operations
            if (response.status === 403) {
                return response.json().then(data => {
                    throw new Error(`BLOCKED_OPERATION: ${data.error || 'Operation blocked'}`);
                });
            }
            // For other errors, try to get the error message from the response
            return response.json().then(data => {
                console.log('Error response data:', data);
                throw new Error(`HTTP ${response.status}: ${data.error || 'Unknown error'}`);
            }).catch(parseError => {
                console.log('Could not parse error response:', parseError);
                // If we can't parse the JSON, just throw the status error
                throw new Error(`HTTP error! status: ${response.status}`);
            });
        }
        return response.json();
    })
    .then(data => {
        console.log('Received data:', data);
        if (data.error) {
            nlInput.value = `Error: ${data.error}`;
        } else {
            nlInput.value = data.english;
        }
    })
    .catch(error => {
        console.error('Error converting to English:', error);
        nlInput.value = `Error: ${error.message}`;
    });
}

// Voice input functionality
let isRecording = false;
let recognition = null;

function toggleVoiceInput() {
    console.log('toggleVoiceInput called');
    const voiceButton = document.getElementById('voiceBtn');
    const micIcon = voiceButton.querySelector('i');
    console.log('Voice button found:', voiceButton);

    if (!recognition) {
        console.log('Initializing speech recognition');
        if ('webkitSpeechRecognition' in window) {
            recognition = new webkitSpeechRecognition();
            recognition.continuous = false;
            recognition.interimResults = false;
            recognition.lang = 'en-US';

            recognition.onstart = function() {
                console.log('Speech recognition started');
                isRecording = true;
                voiceButton.classList.add('recording');
                micIcon.classList.remove('fa-microphone');
                micIcon.classList.add('fa-stop');
            };

            recognition.onresult = function(event) {
                console.log('Speech recognition result:', event.results[0][0].transcript);
                const transcript = event.results[0][0].transcript;
                document.getElementById('nlInput').value = transcript;
                isRecording = false;
                voiceButton.classList.remove('recording');
                micIcon.classList.remove('fa-stop');
                micIcon.classList.add('fa-microphone');
            };

            recognition.onerror = function(event) {
                console.error('Speech recognition error:', event.error);
                isRecording = false;
                voiceButton.classList.remove('recording');
                micIcon.classList.remove('fa-stop');
                micIcon.classList.add('fa-microphone');
                alert('Error with speech recognition: ' + event.error);
            };

            recognition.onend = function() {
                console.log('Speech recognition ended');
                isRecording = false;
                voiceButton.classList.remove('recording');
                micIcon.classList.remove('fa-stop');
                micIcon.classList.add('fa-microphone');
            };
        } else {
            console.error('Speech recognition not supported');
            alert('Speech recognition is not supported in your browser.');
            return;
        }
    }

    if (!isRecording) {
        try {
            console.log('Starting speech recognition');
            recognition.start();
        } catch (error) {
            console.error('Error starting speech recognition:', error);
            isRecording = false;
            voiceButton.classList.remove('recording');
            micIcon.classList.remove('fa-stop');
            micIcon.classList.add('fa-microphone');
            alert('Error starting speech recognition: ' + error.message);
        }
    } else {
        console.log('Stopping speech recognition');
        recognition.stop();
        isRecording = false;
        voiceButton.classList.remove('recording');
        micIcon.classList.remove('fa-stop');
        micIcon.classList.add('fa-microphone');
    }
}