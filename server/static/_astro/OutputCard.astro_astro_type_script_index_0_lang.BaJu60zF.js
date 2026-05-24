import{a as d}from"./api.CNIzsgYS.js";import{e as r}from"./InputCard.astro_astro_type_script_index_0_lang.sWolJfHv.js";let p=[],E=[];async function i(){try{return p=(await d("GET","api/outputs")).outputs||[],L(),p}catch(e){return console.error("Failed to fetch outputs:",e),[]}}async function h(e){try{return await d("POST","api/outputs",e),r("Salida añadida correctamente","success"),await i(),!0}catch(t){const a=t instanceof Error?t.message:String(t);return r(`Error al añadir salida: ${a}`,"error"),!1}}async function x(e){try{return await d("DELETE",`api/outputs/${encodeURIComponent(e)}`),r("Salida eliminada","success"),await i(),!0}catch(t){const a=t instanceof Error?t.message:String(t);return r(`Error al eliminar: ${a}`,"error"),!1}}async function $(e,t){try{return await d("POST",`api/outputs/${encodeURIComponent(e)}/toggle`,{enabled:t}),await i(),!0}catch(a){const n=a instanceof Error?a.message:String(a);return r(`Error: ${n}`,"error"),!1}}function L(){E.forEach(e=>e(p))}function w(e){return{web:"🌐",recording:"⏺",srt:"📡",rtmp:"📺",file:"📁",hls:"🌐"}[e]||"📤"}function I(e){return{web:"HLS",recording:"REC",srt:"SRT",rtmp:"RTMP",file:"FILE",hls:"HLS"}[e]||e.toUpperCase()}let o=null,c=null;function k(){const e=document.createElement("div");if(e.id="confirm-modal",e.className="confirm-modal-overlay hidden",e.setAttribute("role","dialog"),e.setAttribute("aria-modal","true"),e.setAttribute("aria-labelledby","confirm-title"),e.setAttribute("aria-describedby","confirm-message"),e.innerHTML=`
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
    `,document.head.appendChild(t)}return e.querySelector("#btn-confirm-cancel")?.addEventListener("click",()=>{u(!1)}),e.querySelector("#btn-confirm-ok")?.addEventListener("click",()=>{u(!0)}),e.addEventListener("click",t=>{t.target===e&&u(!1)}),e.addEventListener("keydown",t=>{t.key==="Escape"&&u(!1)}),e}function B(e){o||(o=k(),document.body.appendChild(o));const t=o.querySelector("#confirm-message");t&&(t.textContent=e),o.classList.remove("hidden"),requestAnimationFrame(()=>{o?.classList.add("visible")}),setTimeout(()=>{o?.querySelector("#btn-confirm-cancel")?.focus()},100)}function u(e){o&&(o.classList.remove("visible"),setTimeout(()=>{o?.classList.add("hidden"),c&&(c(e),c=null)},300))}async function S(e){return new Promise(t=>{c=t,B(e)})}async function _(e){return S(`¿Eliminar "${e}"?`)}let l=[];const s=new Set;function g(){const e=document.getElementById("outputs-list");if(e){if(e.innerHTML="",l.length===0){e.innerHTML='<div class="output-empty">Sin salidas configuradas</div>';return}l.forEach(t=>{const a=s.has(t.name),n=document.createElement("div");n.className=`output-item${t.state==="running"?" active":""}`;let m="";t.stream_info&&(m=`
          <div class="output-details">
            ${Object.entries(t.stream_info).slice(0,6).map(([v,b])=>`
              <div class="output-detail">
                <span class="output-detail-label">${v}</span>
                <span class="output-detail-value">${b}</span>
              </div>
            `).join("")}
          </div>
        `),n.innerHTML=`
        <div class="output-item-header" data-output-header="${t.name}" role="button" tabindex="0" aria-expanded="${a}" data-output-header-btn="${t.name}">
          <span class="output-collapse-icon${a?" expanded":""}">▶</span>
          <span class="output-item-title">${w(t.type)} ${t.name}</span>
          <span class="output-type-badge">${I(t.type)}</span>
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
          ${m}
          <div class="output-item-actions">
            <button class="btn-remove-output" data-output-remove="${t.name}">🗑️ Eliminar</button>
          </div>
        </div>
      `,e.appendChild(n)}),O()}}function f(e,t){const a=document.querySelector(`[data-output-body="${e}"]`),n=t.querySelector(".output-collapse-icon");s.has(e)?(s.delete(e),a?.classList.remove("expanded"),n?.classList.remove("expanded"),t.setAttribute("aria-expanded","false")):(s.add(e),a?.classList.add("expanded"),n?.classList.add("expanded"),t.setAttribute("aria-expanded","true"))}function O(){document.querySelectorAll("[data-output-header]").forEach(e=>{e.addEventListener("click",t=>{const a=t.currentTarget.dataset.outputHeader;a&&f(a,t.currentTarget)}),e.addEventListener("keydown",t=>{if(t.key==="Enter"||t.key===" "){t.preventDefault();const a=t.currentTarget.dataset.outputHeader;a&&f(a,t.currentTarget)}})}),document.querySelectorAll("[data-output-toggle]").forEach(e=>{e.addEventListener("change",async t=>{const a=t.target.dataset.outputToggle,n=t.target.checked;a&&await $(a,n)})}),document.querySelectorAll("[data-output-toggle-label]").forEach(e=>{e.addEventListener("click",t=>{t.stopPropagation()})}),document.querySelectorAll("[data-output-remove]").forEach(e=>{e.addEventListener("click",async t=>{const a=t.target.dataset.outputRemove;a&&await _(a)&&await x(a)})})}function y(){const e=document.getElementById("btn-add-output-toggle"),t=document.getElementById("add-output-form"),a=e?.querySelector(".add-icon");t&&t.classList.toggle("expanded"),a&&a.classList.toggle("expanded"),t?.classList.contains("expanded")?t.style.display="flex":t&&(t.style.display="none")}function C(e){document.querySelectorAll(".output-type-settings").forEach(a=>{a.style.display="none"});const t=document.getElementById(`settings-${e}`);t&&(t.style.display="flex")}async function T(){const e=document.getElementById("new-output-type")?.value||"web",t=Date.now(),a=`${e}_${t}`;let n={type:e,name:a};e==="web"?n=Object.assign({},n,{segment_duration:parseInt(document.getElementById("output-web-segment")?.value||"4"),list_size:parseInt(document.getElementById("output-web-list")?.value||"6"),audio_offset_ms:0,encoder_mode:"auto"}):e==="recording"?n=Object.assign({},n,{output_path:document.getElementById("output-recording-path")?.value||"./output/recording.mp4",format:document.getElementById("output-recording-format")?.value||"mp4",codec:"aac",audio_codec:"aac"}):e==="srt"?n=Object.assign({},n,{url:document.getElementById("output-srt-url")?.value||"srt://localhost:9001",mode:document.getElementById("output-srt-mode")?.value||"caller",latency_ms:parseInt(document.getElementById("output-srt-latency")?.value||"2000"),video_bitrate:document.getElementById("output-srt-vbitrate")?.value||"2500k",audio_bitrate:document.getElementById("output-srt-abitrate")?.value||"128k"}):e==="rtmp"?n=Object.assign({},n,{url:document.getElementById("output-rtmp-url")?.value||"rtmp://localhost/live/stream",video_bitrate:document.getElementById("output-rtmp-vbitrate")?.value||"2500k",audio_bitrate:document.getElementById("output-rtmp-abitrate")?.value||"128k",encoder_mode:"auto"}):e==="file"&&(n=Object.assign({},n,{output_path:document.getElementById("output-file-path")?.value||"./output",save_video:document.getElementById("output-file-video")?.value==="true",save_audio:document.getElementById("output-file-audio")?.value==="true",save_subs:document.getElementById("output-file-subs")?.value==="true"})),await h({name:a,type:e,config:n})&&(s.add(a),y())}document.getElementById("btn-add-output-toggle")?.addEventListener("click",y);document.getElementById("btn-create-output")?.addEventListener("click",T);document.getElementById("new-output-type")?.addEventListener("change",e=>{C(e.target.value)});l=await i().catch(()=>[]);g();setInterval(async()=>{l=await i().catch(()=>[]),g()},5e3);
