// js/shared_databases.js
document.addEventListener("DOMContentLoaded", () => {
    const user = JSON.parse(localStorage.getItem("currentUser"));
    if (!user) return (window.location.href = "login.html");
  
    fetch(`http://127.0.0.1:5001/get-databases?user_id=${user.user_id}`)
      .then((res) => res.json())
      .then((data) => {
        const sharedDatabases = data.shared || [];
        const dbGrid = document.getElementById("dbGrid");
        dbGrid.innerHTML = "";
  
        if (sharedDatabases.length === 0) {
          dbGrid.innerHTML = `<p style="color: gray;">No shared databases found.</p>`;
          return;
        }
  
        sharedDatabases.forEach((db) => {
          const card = document.createElement("div");
          card.className = "db-card";
  
          const name = document.createElement("h3");
          name.textContent = db.db_name + " (shared)";
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
        console.error("Failed to fetch shared databases:", err);
        document.getElementById("dbGrid").innerHTML = `<p style="color: red;">Failed to load shared databases.</p>`;
      });
  });
  
  function logout() {
    localStorage.removeItem("currentUser");
    window.location.href = "login.html";
  }
  