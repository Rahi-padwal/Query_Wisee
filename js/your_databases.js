document.addEventListener("DOMContentLoaded", () => {
    const user = JSON.parse(localStorage.getItem("currentUser"));
    if (!user) {
      window.location.href = "login.html";
      return;
    }
  
    fetch(`http://127.0.0.1:5501/get-databases?user_id=${user.user_id}`)
      .then((res) => res.json())
      .then((data) => {
        const ownDatabases = data.own || [];
        const dbGrid = document.getElementById("dbGrid");
        dbGrid.innerHTML = "";
  
        if (ownDatabases.length === 0) {
          dbGrid.innerHTML = `<p style="color: gray;">No databases found. Import your first database to get started!</p>`;
          return;
        }
  
        ownDatabases.forEach((db) => {
          const card = document.createElement("div");
          card.className = "db-card";
  
          // Trash icon (top right)
          const trash = document.createElement("span");
          trash.innerHTML = "&#128465;"; // Unicode trash can
          trash.className = "trash-icon";
          trash.title = "Delete database";
          trash.style.cssText = "position:absolute;top:8px;right:12px;cursor:pointer;font-size:1.2em;color:#c00;z-index:2;";
          trash.onclick = (e) => {
            e.stopPropagation();
            if (confirm(`Are you sure you want to delete '${db.db_name}'?`)) {
              fetch('http://127.0.0.1:5501/delete-database', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  user_id: db.user_id,
                  db_name: db.db_name,
                  db_type: db.db_type,
                  db_id: db.db_id
                })
              })
                .then(res => res.json())
                .then(result => {
                  if (result.message) {
                    card.remove();
                  } else {
                    alert(result.error || 'Failed to delete database.');
                  }
                })
                .catch(() => alert('Failed to delete database.'));
            }
          };
          card.style.position = "relative";
          card.appendChild(trash);
  
          const name = document.createElement("h3");
          name.textContent = db.db_name;
          card.appendChild(name);
  
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
  
          dbGrid.appendChild(card);
        });
      })
      .catch((err) => {
        console.error("Failed to fetch databases:", err);
        document.getElementById("dbGrid").innerHTML = `<p style="color: red;">Failed to load databases.</p>`;
      });
  });
  
  function logout() {
    localStorage.removeItem("currentUser");
    window.location.href = "login.html";
  }
  