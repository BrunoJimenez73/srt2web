import{a as m}from"./api.BpNi2mzZ.js";import{s as r}from"./index.BpSbb1Lw.js";let p=[],b=[];async function u(){try{return p=(await m("GET","api/outputs")).outputs||[],I(),p}catch(e){return console.error("Failed to fetch outputs:",e),[]}}async function E(e){try{return await m("POST","api/outputs",e),r("Salida añadida correctamente","success"),await u(),!0}catch(t){const a=t instanceof Error?t.message:String(t);return r(`Error al añadir salida: ${a}`,"error"),!1}}async function h(e){try{return await m("DELETE",`api/outputs/${encodeURIComponent(e)}`),r("Salida eliminada","success"),await u(),!0}catch(t){const a=t instanceof Error?t.message:String(t);return r(`Error al eliminar: ${a}`,"error"),!1}}async function x(e,t){try{return await m("POST",`api/outputs/${encodeURIComponent(e)}/toggle`,{enabled:t}),await u(),!0}catch(a){const n=a instanceof Error?a.message:String(a);return r(`Error: ${n}`,"error"),!1}}function I(){b.forEach(e=>e(p))}function L(e){return{web:"🌐",recording:"⏺",srt:"📡",rtmp:"📺",file:"📁",hls:"🌐"}[e]||"📤"}function $(e){return{web:"HLS",recording:"REC",srt:"SRT",rtmp:"RTMP",file:"FILE",hls:"HLS"}[e]||e.toUpperCase()}let o=null,l=null;function w(){const e=document.createElement("div");if(e.id="confirm-modal",e.className="confirm-modal-overlay hidden",e.setAttribute("role","dialog"),e.setAttribute("aria-modal","true"),e.setAttribute("aria-labelledby","confirm-title"),e.setAttribute("aria-describedby","confirm-message"),e.innerHTML=`
    <div class="confirm-modal-content" role="document">
      <h3 id="confirm-title" class="confirm-title">Confirmación</h3>
      <p id="confirm-message" class="confirm-message"></p>
      <div class="confirm-buttons">
        <button id="btn-confirm-cancel" class="btn btn-ghost" aria-label="Cancelar">
          Cancelar
        </button>
        <button id="btn-confirm-ok" class="btn btn-error" aria-label="Confirmar">
          Confirmar
        </button>
      </div>
    </div>
  `,!document.getElementById("confirm-modal-styles")){const t=document.createElement("style");t.id="confirm-modal-styles",t.textContent=`
      .confirm-modal-overlay {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
        opacity: 0;
        transition: opacity 0.3s ease;
      }
      
      .confirm-modal-overlay.visible {
        opacity: 1;
      }
      
      .confirm-modal-content {
        background: var(--color-card, #1a1a24);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 24px;
        max-width: 400px;
        width: 90%;
        transform: scale(0.9);
        transition: transform 0.3s ease;
      }
      
      .confirm-modal-overlay.visible .confirm-modal-content {
        transform: scale(1);
      }
      
      .confirm-title {
        font-size: 16px;
        font-weight: 600;
        color: var(--color-surface-light, #e4e4e8);
        margin-bottom: 8px;
      }
      
      .confirm-message {
        font-size: 13px;
        color: var(--color-surface-dim, #8888a0);
        margin-bottom: 20px;
        line-height: 1.5;
      }
      
      .confirm-buttons {
        display: flex;
        gap: 8px;
        justify-content: flex-end;
      }
    `,document.head.appendChild(t)}return e.querySelector("#btn-confirm-cancel")?.addEventListener("click",()=>{c(!1)}),e.querySelector("#btn-confirm-ok")?.addEventListener("click",()=>{c(!0)}),e.addEventListener("click",t=>{t.target===e&&c(!1)}),e.addEventListener("keydown",t=>{t.key==="Escape"&&c(!1)}),e}function B(e){o||(o=w(),document.body.appendChild(o));const t=o.querySelector("#confirm-message");t&&(t.textContent=e),o.classList.remove("hidden"),requestAnimationFrame(()=>{o?.classList.add("visible")}),setTimeout(()=>{o?.querySelector("#btn-confirm-cancel")?.focus()},100)}function c(e){o&&(o.classList.remove("visible"),setTimeout(()=>{o?.classList.add("hidden"),l&&(l(e),l=null)},300))}async function S(e){return new Promise(t=>{l=t,B(e)})}async function k(e){return S(`¿Eliminar "${e}"?`)}let d=[];const i=new Set;function f(){const e=document.getElementById("outputs-list");if(e){if(e.innerHTML="",d.length===0){e.innerHTML='<div class="output-empty">Sin salidas configuradas</div>';return}d.forEach(t=>{const a=i.has(t.name),n=document.createElement("div");n.className=`output-item${t.state==="running"?" active":""}`;let s="";t.stream_info&&(s=`
          <div class="output-details">
            ${Object.entries(t.stream_info).slice(0,6).map(([y,v])=>`
              <div class="output-detail">
                <span class="output-detail-label">${y}</span>
                <span class="output-detail-value">${v}</span>
              </div>
            `).join("")}
          </div>
        `),n.innerHTML=`
        <div class="output-item-header" data-output-header="${t.name}">
          <span class="output-collapse-icon${a?" expanded":""}">▶</span>
          <span class="output-item-title">${L(t.type)} ${t.name}</span>
          <span class="output-type-badge">${$(t.type)}</span>
          <label class="output-card-toggle" data-output-toggle-label="${t.name}">
            <input type="checkbox" ${t.enabled?"checked":""} data-output-toggle="${t.name}" />
            <span class="toggle-slider${t.enabled?" on":""}"></span>
          </label>
        </div>
        <div class="output-item-body${a?" expanded":""}" data-output-body="${t.name}">
          <div class="output-stats">
            <div class="output-stat">
              <span class="output-stat-label">Chunks</span>
              <span class="output-stat-value">${t.processed_chunks}</span>
            </div>
            <div class="output-stat">
              <span class="output-stat-label">Estado</span>
              <span class="output-stat-value ${t.state==="running"?"success":t.state==="error"?"error":""}">${t.state}</span>
            </div>
          </div>
          ${t.error?`<div class="output-stat-value error" style="padding: 8px; margin-bottom: 8px;">${t.error}</div>`:""}
          ${s}
          <div class="output-item-actions">
            <button class="btn-remove-output" data-output-remove="${t.name}">🗑️ Eliminar</button>
          </div>
        </div>
      `,e.appendChild(n)}),_()}}function _(){document.querySelectorAll("[data-output-header]").forEach(e=>{e.addEventListener("click",t=>{const a=t.currentTarget.dataset.outputHeader;if(a){const n=document.querySelector(`[data-output-body="${a}"]`),s=t.currentTarget.querySelector(".output-collapse-icon");i.has(a)?(i.delete(a),n?.classList.remove("expanded"),s?.classList.remove("expanded")):(i.add(a),n?.classList.add("expanded"),s?.classList.add("expanded"))}})}),document.querySelectorAll("[data-output-toggle]").forEach(e=>{e.addEventListener("change",async t=>{const a=t.target.dataset.outputToggle,n=t.target.checked;a&&await x(a,n)})}),document.querySelectorAll("[data-output-toggle-label]").forEach(e=>{e.addEventListener("click",t=>{t.stopPropagation()})}),document.querySelectorAll("[data-output-remove]").forEach(e=>{e.addEventListener("click",async t=>{const a=t.target.dataset.outputRemove;a&&await k(a)&&await h(a)})})}function g(){const e=document.getElementById("btn-add-output-toggle"),t=document.getElementById("add-output-form"),a=e?.querySelector(".add-icon");t&&t.classList.toggle("expanded"),a&&a.classList.toggle("expanded"),t?.classList.contains("expanded")?t.style.display="flex":t&&(t.style.display="none")}function C(e){document.querySelectorAll(".output-type-settings").forEach(a=>{a.style.display="none"});const t=document.getElementById(`settings-${e}`);t&&(t.style.display="flex")}async function O(){const e=document.getElementById("new-output-type")?.value||"web",t=Date.now(),a=`${e}_${t}`;let n={type:e,name:a};e==="web"?n=Object.assign({},n,{segment_duration:parseInt(document.getElementById("output-web-segment")?.value||"4"),list_size:parseInt(document.getElementById("output-web-list")?.value||"6"),audio_offset_ms:0,encoder_mode:"auto"}):e==="recording"?n=Object.assign({},n,{output_path:document.getElementById("output-recording-path")?.value||"./output/recording.mp4",format:document.getElementById("output-recording-format")?.value||"mp4",codec:"aac",audio_codec:"aac"}):e==="srt"?n=Object.assign({},n,{url:document.getElementById("output-srt-url")?.value||"srt://localhost:9001",mode:document.getElementById("output-srt-mode")?.value||"caller",latency_ms:parseInt(document.getElementById("output-srt-latency")?.value||"2000"),video_bitrate:document.getElementById("output-srt-vbitrate")?.value||"2500k",audio_bitrate:document.getElementById("output-srt-abitrate")?.value||"128k"}):e==="rtmp"?n=Object.assign({},n,{url:document.getElementById("output-rtmp-url")?.value||"rtmp://localhost/live/stream",video_bitrate:document.getElementById("output-rtmp-vbitrate")?.value||"2500k",audio_bitrate:document.getElementById("output-rtmp-abitrate")?.value||"128k",encoder_mode:"auto"}):e==="file"&&(n=Object.assign({},n,{output_path:document.getElementById("output-file-path")?.value||"./output",save_video:document.getElementById("output-file-video")?.value==="true",save_audio:document.getElementById("output-file-audio")?.value==="true",save_subs:document.getElementById("output-file-subs")?.value==="true"})),await E({name:a,type:e,config:n})&&(i.add(a),g())}document.getElementById("btn-add-output-toggle")?.addEventListener("click",g);document.getElementById("btn-create-output")?.addEventListener("click",O);document.getElementById("new-output-type")?.addEventListener("change",e=>{C(e.target.value)});d=await u().catch(()=>[]);f();setInterval(async()=>{d=await u().catch(()=>[]),f()},5e3);
