// js/dashboard.js

let cachedData = { own: [], shared: [] };

document.addEventListener("DOMContentLoaded", () => {
  const user = JSON.parse(localStorage.getItem("currentUser"));
  if (!user) {
    window.location.href = "login.html";
    return;
  }

  fetch(`http://127.0.0.1:5501/get-databases?user_id=${user.user_id}`)
    .then((res) => res.json())
    .then((data) => {
      cachedData = data;
      document.getElementById("yourDBCount").textContent = `${data.own.length} database(s)`;
    })
    .catch((err) => {
      console.error("Failed to fetch databases:", err);
    });

  document.querySelector(".import-btn").addEventListener("click", showImportDialog);

  document.getElementById("importDialog").addEventListener("click", function (e) {
    if (e.target === this) {
      closeImportDialog();
    }
  });
});

function logout() {
  localStorage.removeItem("currentUser");
  window.location.href = "login.html";
}

function showCategory(type) {
  const dbGrid = document.getElementById("dbGrid");
  dbGrid.style.display = "grid";
  dbGrid.innerHTML = "";

  const list = cachedData[type] || [];
  if (list.length === 0) {
    dbGrid.innerHTML = `<p style="color: gray;">No databases found in this category.</p>`;
    return;
  }

  list.forEach((db) => {
    const card = document.createElement("div");
    card.className = "db-card";

    const name = document.createElement("h3");
    name.textContent = db.db_name + (type === "shared" ? " (shared)" : "");
    card.appendChild(name);

    // Add database type line
    const typeLine = document.createElement("p");
    // If you have a more specific type for cloud DBs, use db.cloud_type or similar
    let displayType = db.db_type;
    if (db.db_type === "cloud" && db.cloud_type) {
      displayType = db.cloud_type + " (Cloud)";
    } else if (db.db_type === "cloud") {
      displayType = "Cloud";
    }
    typeLine.textContent = `Type: ${displayType}`;
    typeLine.style.fontSize = "0.95rem";
    typeLine.style.color = "#555";
    card.appendChild(typeLine);

    if (db.created_at) {
      const date = document.createElement("p");
      const formattedDate = new Date(db.created_at).toLocaleDateString();
      date.textContent = `Imported on: ${formattedDate}`;
      date.style.fontSize = "0.9rem";
      date.style.color = "gray";
      card.appendChild(date);
    }

    const btn = document.createElement("button");
    btn.textContent = "Open";
    btn.className = "btn primary small";
    btn.onclick = () => {
      localStorage.setItem("selectedDB", JSON.stringify(db));
      window.location.href = `workspace.html?db=${encodeURIComponent(db.db_name)}`;
    };
    card.appendChild(btn);

    // Add share button for cloud DBs
    if (db.db_type === "cloud") {
      const shareBtn = document.createElement("button");
      shareBtn.textContent = "Share";
      shareBtn.className = "btn secondary small";
      shareBtn.onclick = () => {
        // TODO: Implement your share logic here (e.g., open share dialog, copy link, etc.)
        alert(`Share link for ${db.db_name}`);
      };
      card.appendChild(shareBtn);
    }

    dbGrid.appendChild(card);
  });
}

function showImportDialog() {
  document.getElementById("importDialog").style.display = "flex";
}

function closeImportDialog() {
  document.getElementById("importDialog").style.display = "none";
}

function importFromMySQL() {
  closeImportDialog();
  document.getElementById("mysqlImportDialog").style.display = "flex";
}

function closeMySQLImportDialog() {
  document.getElementById("mysqlImportDialog").style.display = "none";
}

function submitMySQLImport(event) {
  event.preventDefault();
  const user = JSON.parse(localStorage.getItem("currentUser"));
  if (!user) {
    window.location.href = "login.html";
    return;
  }
  
  const db_name = document.getElementById("mysqlDbName").value;
  const username = document.getElementById("mysqlUsername").value;
  const password = document.getElementById("mysqlPassword").value;
  
  fetch("http://127.0.0.1:5501/import-database", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_id: user.user_id,
      db_name,
      db_type: "local",
      username,
      password
    })
  })
    .then((res) => res.json())
    .then((data) => {
      if (data.error) {
        alert(data.error);
      } else {
        alert(data.message);
        location.reload();
      }
    })
    .catch((err) => {
      alert("Failed to connect to backend.");
      console.error(err);
    });
  closeMySQLImportDialog();
}

function importFromCloud() {
  closeImportDialog();
  document.getElementById("cloudImportDialog").style.display = "flex";
}

function closeCloudImportDialog() {
  document.getElementById("cloudImportDialog").style.display = "none";
}

function submitCloudImport(event) {
  event.preventDefault();
  const user = JSON.parse(localStorage.getItem("currentUser"));
  if (!user) {
    window.location.href = "login.html";
    return;
  }
  const host_url = document.getElementById("cloudHostUrl").value;
  const username = document.getElementById("cloudUsername").value;
  const password = document.getElementById("cloudPassword").value;
  const db_name = document.getElementById("cloudDbName").value;
  fetch("http://127.0.0.1:5501/import-cloud-database", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_id: user.user_id,
      db_name,
      host_url,
      username,
      password,
      db_type: "cloud"
    })
  })
    .then((res) => res.json())
    .then((data) => {
      if (data.error) {
        alert(data.error);
      } else {
        alert(data.message);
        location.reload();
      }
    })
    .catch((err) => {
      alert("Failed to connect to backend.");
      console.error(err);
    });
  closeCloudImportDialog();
}

function importFromMongoDB() {
  closeImportDialog();
  document.getElementById("mongoImportDialog").style.display = "flex";
}

function closeMongoImportDialog() {
  document.getElementById("mongoImportDialog").style.display = "none";
}

function submitMongoImport(event) {
  event.preventDefault();
  const user = JSON.parse(localStorage.getItem("currentUser"));
  if (!user) {
    window.location.href = "login.html";
    return;
  }
  
  const db_name = document.getElementById("mongoDbName").value;
  const username = document.getElementById("mongoUsername").value.trim();
  const password = document.getElementById("mongoPassword").value.trim();
  
  // Only include credentials if both username and password are provided
  const requestBody = {
    user_id: user.user_id,
    db_name,
    db_type: "mongodb"
  };
  
  // Add credentials only if both username and password are provided
  if (username && password) {
    requestBody.username = username;
    requestBody.password = password;
  } else if (username || password) {
    alert("Please provide both username and password, or leave both empty for no authentication.");
    return;
  }
  
  fetch("http://127.0.0.1:5501/import-mongodb", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(requestBody)
  })
    .then((res) => res.json())
    .then((data) => {
      if (data.error) {
        alert(data.error);
      } else {
        alert(data.message);
        location.reload();
      }
    })
    .catch((err) => {
      alert("Failed to connect to backend.");
      console.error(err);
    });
  closeMongoImportDialog();
}
