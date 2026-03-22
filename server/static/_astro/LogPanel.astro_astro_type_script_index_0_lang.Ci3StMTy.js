import{f as d}from"./utils.CxOrwHNO.js";const n=document.getElementById("log-content"),r=document.querySelector(".log-panel"),g=500,i=document.getElementById("log-empty"),m=document.getElementById("log-search");let o="",c=!1;function p(){r&&(c=!c,r.classList.toggle("collapsed",c))}function u(e,s,l){if(!n)return;i&&i.parentElement===n&&i.remove();const t=document.createElement("div");t.className="log-entry",t.setAttribute("role","listitem"),t.dataset.level=e,t.dataset.message=s.toLowerCase();const a=l?d(l):new Date().toLocaleTimeString("es-ES");for(t.innerHTML=`
      <span class="log-timestamp">${a}</span>
      <span class="log-level ${e}">[${e.toUpperCase()}]</span>
      <span class="log-message">${y(s)}</span>
    `,o&&!t.dataset.message.includes(o.toLowerCase())&&(t.style.display="none"),n.appendChild(t);n.children.length>g;)n.removeChild(n.firstChild);n.scrollTop=n.scrollHeight}m?.addEventListener("input",e=>{o=e.target.value,n?.querySelectorAll(".log-entry")?.forEach(l=>{const t=l;if(o){const a=t.dataset.message?.includes(o.toLowerCase());t.style.display=a?"":"none"}else t.style.display=""})});function y(e){const s=document.createElement("div");return s.textContent=e,s.innerHTML}window.addLog=u;window.toggleLogPanel=p;window.clearLogs=function(){if(n){n.innerHTML="";const e=document.createElement("div");e.className="log-empty",e.id="log-empty",e.innerHTML=`
        <span class="log-empty-icon">📝</span>
        <span class="log-empty-text">Sin registros aún</span>
      `,n.appendChild(e)}};
