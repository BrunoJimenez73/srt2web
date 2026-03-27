import{f as c}from"./utils.CxOrwHNO.js";const n=document.getElementById("log-content"),r=500,i=document.getElementById("log-empty"),d=document.getElementById("log-search");let o="";function m(e,s,a){if(!n)return;i&&i.parentElement===n&&i.remove();const t=document.createElement("div");t.className="log-entry",t.setAttribute("role","listitem"),t.dataset.level=e,t.dataset.message=s.toLowerCase();const l=a?c(a):new Date().toLocaleTimeString("es-ES");for(t.innerHTML=`
      <span class="log-timestamp">${l}</span>
      <span class="log-level ${e}">[${e.toUpperCase()}]</span>
      <span class="log-message">${p(s)}</span>
    `,o&&!t.dataset.message.includes(o.toLowerCase())&&(t.style.display="none"),n.appendChild(t);n.children.length>r;)n.removeChild(n.firstChild);n.scrollTop=n.scrollHeight}d?.addEventListener("input",e=>{o=e.target.value,n?.querySelectorAll(".log-entry")?.forEach(a=>{const t=a;if(o){const l=t.dataset.message?.includes(o.toLowerCase());t.style.display=l?"":"none"}else t.style.display=""})});function p(e){const s=document.createElement("div");return s.textContent=e,s.innerHTML}window.addLog=m;window.clearLogs=function(){if(n){n.innerHTML="";const e=document.createElement("div");e.className="log-empty",e.id="log-empty",e.innerHTML=`
        <span class="log-empty-icon">📝</span>
        <span class="log-empty-text">Sin registros aún</span>
      `,n.appendChild(e)}};
