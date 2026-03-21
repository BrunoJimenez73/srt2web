import{f as l}from"./utils.CxOrwHNO.js";const e=document.getElementById("log-content"),i=500;function c(n,t,s){if(!e)return;const o=document.createElement("div");o.className="log-entry";const a=s?l(s):new Date().toLocaleTimeString("es-ES");for(o.innerHTML=`
      <span class="log-timestamp">${a}</span>
      <span class="log-level ${n}">[${n.toUpperCase()}]</span>
      <span class="log-message">${r(t)}</span>
    `,e.appendChild(o);e.children.length>i;)e.removeChild(e.firstChild);e.scrollTop=e.scrollHeight}function r(n){const t=document.createElement("div");return t.textContent=n,t.innerHTML}window.addLog=c;window.clearLogs=function(){e&&(e.innerHTML="")};
