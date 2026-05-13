const state = {
  projects: [],
  project: null,
  projectId: null,
  documents: [],
  classes: [],
  properties: [],
  entities: [],
  relations: [],
  graph: null,
  candidates: [],
  lastExtractionSummary: null,
  editingClassId: null,
  editingPropertyId: null,
  editingRelationId: null,
  currentEvidence: null,
};

const STORAGE_KEY = "ontoforge.projectId";

const els = {
  createProjectForm: document.getElementById("createProjectForm"),
  projectName: document.getElementById("projectName"),
  projectDescription: document.getElementById("projectDescription"),
  projectSelect: document.getElementById("projectSelect"),
  projectMeta: document.getElementById("projectMeta"),
  refreshProjectsBtn: document.getElementById("refreshProjectsBtn"),
  reloadWorkspaceBtn: document.getElementById("reloadWorkspaceBtn"),
  syncGraphBtn: document.getElementById("syncGraphBtn"),
  exportRdfBtn: document.getElementById("exportRdfBtn"),
  exportOwlBtn: document.getElementById("exportOwlBtn"),
  exportJsonldBtn: document.getElementById("exportJsonldBtn"),
  exportTurtleBtn: document.getElementById("exportTurtleBtn"),
  graphHealthBadge: document.getElementById("graphHealthBadge"),
  statusMessage: document.getElementById("statusMessage"),
  uploadDocumentForm: document.getElementById("uploadDocumentForm"),
  documentFile: document.getElementById("documentFile"),
  uploadOntologyForm: document.getElementById("uploadOntologyForm"),
  ontologyFile: document.getElementById("ontologyFile"),
  generateCandidatesBtn: document.getElementById("generateCandidatesBtn"),
  runExtractionBtn: document.getElementById("runExtractionBtn"),
  candidateLimit: document.getElementById("candidateLimit"),
  candidateTermLength: document.getElementById("candidateTermLength"),
  extractionSummary: document.getElementById("extractionSummary"),
  candidateResults: document.getElementById("candidateResults"),
  documentsTable: document.getElementById("documentsTable"),
  ontologyTree: document.getElementById("ontologyTree"),
  createClassForm: document.getElementById("createClassForm"),
  classFormTitle: document.getElementById("classFormTitle"),
  classSubmitBtn: document.getElementById("classSubmitBtn"),
  classCancelBtn: document.getElementById("classCancelBtn"),
  className: document.getElementById("className"),
  classLabel: document.getElementById("classLabel"),
  classDescription: document.getElementById("classDescription"),
  classParentSelect: document.getElementById("classParentSelect"),
  createPropertyForm: document.getElementById("createPropertyForm"),
  propertyFormTitle: document.getElementById("propertyFormTitle"),
  propertySubmitBtn: document.getElementById("propertySubmitBtn"),
  propertyCancelBtn: document.getElementById("propertyCancelBtn"),
  propertyName: document.getElementById("propertyName"),
  propertyLabel: document.getElementById("propertyLabel"),
  propertyDescription: document.getElementById("propertyDescription"),
  propertyType: document.getElementById("propertyType"),
  propertyDatatype: document.getElementById("propertyDatatype"),
  propertyDomainSelect: document.getElementById("propertyDomainSelect"),
  propertyRangeSelect: document.getElementById("propertyRangeSelect"),
  classesTable: document.getElementById("classesTable"),
  propertiesTable: document.getElementById("propertiesTable"),
  createEntityForm: document.getElementById("createEntityForm"),
  entityName: document.getElementById("entityName"),
  entityClassSelect: document.getElementById("entityClassSelect"),
  entityAliases: document.getElementById("entityAliases"),
  createRelationForm: document.getElementById("createRelationForm"),
  relationFormTitle: document.getElementById("relationFormTitle"),
  relationSubmitBtn: document.getElementById("relationSubmitBtn"),
  relationCancelBtn: document.getElementById("relationCancelBtn"),
  relationSubjectSelect: document.getElementById("relationSubjectSelect"),
  relationPredicateSelect: document.getElementById("relationPredicateSelect"),
  relationObjectSelect: document.getElementById("relationObjectSelect"),
  relationLiteralValue: document.getElementById("relationLiteralValue"),
  relationSourceDocumentSelect: document.getElementById("relationSourceDocumentSelect"),
  relationEvidence: document.getElementById("relationEvidence"),
  entitiesTable: document.getElementById("entitiesTable"),
  relationsTable: document.getElementById("relationsTable"),
  evidenceViewer: document.getElementById("evidenceViewer"),
  graphCanvas: document.getElementById("graphCanvas"),
  classCount: document.getElementById("classCount"),
  propertyCount: document.getElementById("propertyCount"),
  entityCount: document.getElementById("entityCount"),
  relationCount: document.getElementById("relationCount"),
  tabs: Array.from(document.querySelectorAll(".tab")),
  tabPanels: Array.from(document.querySelectorAll(".tab-panel")),
};

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function setStatus(message, tone = "neutral") {
  els.statusMessage.textContent = message;
  els.statusMessage.dataset.tone = tone;
}

function setGraphHealthBadge(message, tone = "neutral") {
  els.graphHealthBadge.textContent = message;
  els.graphHealthBadge.className = `pill ${tone}`;
}

async function api(path, options = {}) {
  const response = await fetch(path, options);
  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    const detail = payload?.detail || payload?.message || payload || `Request failed (${response.status})`;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }

  return payload;
}

async function downloadFile(path, filenameFallback) {
  const response = await fetch(path);
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `Download failed (${response.status})`);
  }
  const blob = await response.blob();
  const disposition = response.headers.get("content-disposition") || "";
  const match = disposition.match(/filename="?([^";]+)"?/i);
  const filename = match?.[1] || filenameFallback;
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

function requireProject() {
  if (!state.projectId) {
    setStatus("Please create or select a project first.", "warning");
    return null;
  }
  return state.projectId;
}

function formatDate(value) {
  if (!value) return "—";
  return new Date(value).toLocaleString();
}

function optionMarkup(value, label, selected = false) {
  return `<option value="${escapeHtml(value)}" ${selected ? "selected" : ""}>${escapeHtml(label)}</option>`;
}

function titleCase(value) {
  return String(value || "")
    .split(/[_\s-]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function activateTab(tabName) {
  els.tabs.forEach((tab) => tab.classList.toggle("active", tab.dataset.tab === tabName));
  els.tabPanels.forEach((panel) => panel.classList.toggle("active", panel.id === `tab-${tabName}`));
}

function getClassById(id) {
  return state.classes.find((item) => item.id === Number(id)) || null;
}

function getPropertyById(id) {
  return state.properties.find((item) => item.id === Number(id)) || null;
}

function getRelationById(id) {
  return state.relations.find((item) => item.id === Number(id)) || null;
}

function getEntityById(id) {
  return state.entities.find((item) => item.id === Number(id)) || null;
}

function getDocumentById(id) {
  return state.documents.find((item) => item.id === Number(id)) || null;
}

function renderProjectSelect() {
  if (!state.projects.length) {
    els.projectSelect.innerHTML = optionMarkup("", "No projects yet", true);
    return;
  }

  const selectedId = state.projectId ? String(state.projectId) : "";
  els.projectSelect.innerHTML = state.projects
    .map((project) => optionMarkup(project.id, `${project.name} (#${project.id})`, String(project.id) === selectedId))
    .join("");
}

function renderProjectMeta() {
  if (!state.project) {
    els.projectMeta.innerHTML = "Create or select a project to begin.";
    return;
  }

  els.projectMeta.innerHTML = `
    <strong>${escapeHtml(state.project.name)}</strong>
    <div class="helper-text">Project ID: ${state.project.id}</div>
    <div class="helper-text">${escapeHtml(state.project.description || "No description provided.")}</div>
    <div class="helper-text">Created: ${escapeHtml(formatDate(state.project.created_at))}</div>
  `;
}

function renderExtractionSummary() {
  if (!state.lastExtractionSummary) {
    els.extractionSummary.innerHTML = "No extraction run yet.";
    return;
  }

  const summary = state.lastExtractionSummary;
  els.extractionSummary.innerHTML = `
    <strong>${escapeHtml(summary.message || "Extraction completed.")}</strong>
    <div class="helper-text">Documents processed: ${summary.processed_documents}</div>
    <div class="helper-text">Created entities: ${summary.created_entities} · Reused entities: ${summary.reused_entities}</div>
    <div class="helper-text">Typed entities: ${summary.typed_entities} · Created properties: ${summary.created_properties}</div>
    <div class="helper-text">Created relations: ${summary.created_relations}</div>
  `;
}

function renderDocuments() {
  if (!state.documents.length) {
    els.documentsTable.innerHTML = "No documents uploaded yet.";
    els.documentsTable.classList.add("empty-state");
    return;
  }

  els.documentsTable.classList.remove("empty-state");
  els.documentsTable.innerHTML = `
    <table>
      <thead>
        <tr>
          <th>ID</th>
          <th>Filename</th>
          <th>Type</th>
          <th>Chunks</th>
          <th>Status</th>
          <th>Created</th>
        </tr>
      </thead>
      <tbody>
        ${state.documents
          .map(
            (doc) => `
              <tr>
                <td>${doc.id}</td>
                <td>${escapeHtml(doc.filename)}</td>
                <td>${escapeHtml(doc.content_type || "—")}</td>
                <td>${doc.chunk_count}</td>
                <td>${escapeHtml(doc.status)}</td>
                <td>${escapeHtml(formatDate(doc.created_at))}</td>
              </tr>
            `,
          )
          .join("")}
      </tbody>
    </table>
  `;
}

function renderCandidates() {
  if (!state.candidates.length) {
    els.candidateResults.innerHTML = "Upload documents and generate suggestions to see candidate ontology terms.";
    els.candidateResults.classList.add("empty-state");
    return;
  }

  els.candidateResults.classList.remove("empty-state");
  els.candidateResults.innerHTML = state.candidates
    .map(
      (candidate) => `
        <article class="candidate-card">
          <strong>${escapeHtml(candidate.term)}</strong>
          <p>Frequency: ${candidate.frequency} · Type: ${escapeHtml(candidate.suggested_type)}</p>
          <p>${escapeHtml(candidate.evidence || "No evidence available.")}</p>
          <button type="button" class="ghost small add-candidate-btn" data-term="${escapeHtml(candidate.term)}">Add as class</button>
        </article>
      `,
    )
    .join("");
}

function buildOntologyTreeMarkup(parentId = null) {
  const children = state.classes
    .filter((item) => (item.parent_class_id ?? null) === parentId)
    .sort((a, b) => a.name.localeCompare(b.name));

  if (!children.length) {
    return "";
  }

  return `
    <ul>
      ${children
        .map(
          (item) => `
            <li>
              <div class="tree-node">
                <div class="tree-node-main">
                  <strong>${escapeHtml(item.label || item.name)}</strong>
                  <span class="tree-node-meta">${escapeHtml(item.name)} · ${escapeHtml(item.status)}</span>
                </div>
                <button type="button" class="ghost small edit-class-btn" data-class-id="${item.id}">Edit</button>
              </div>
              ${buildOntologyTreeMarkup(item.id)}
            </li>
          `,
        )
        .join("")}
    </ul>
  `;
}

function renderOntologyTree() {
  if (!state.classes.length) {
    els.ontologyTree.innerHTML = "No ontology classes yet.";
    els.ontologyTree.classList.add("empty-state");
    return;
  }

  els.ontologyTree.classList.remove("empty-state");
  els.ontologyTree.innerHTML = `<div class="tree-list">${buildOntologyTreeMarkup(null)}</div>`;
}

function renderClasses() {
  if (!state.classes.length) {
    els.classesTable.innerHTML = "No ontology classes yet.";
    els.classesTable.classList.add("empty-state");
    return;
  }

  const byId = Object.fromEntries(state.classes.map((item) => [item.id, item]));
  els.classesTable.classList.remove("empty-state");
  els.classesTable.innerHTML = `
    <table>
      <thead>
        <tr>
          <th>ID</th>
          <th>Name</th>
          <th>Label</th>
          <th>Parent</th>
          <th>Status</th>
          <th>Source</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        ${state.classes
          .map(
            (item) => `
              <tr>
                <td>${item.id}</td>
                <td>${escapeHtml(item.name)}</td>
                <td>${escapeHtml(item.label || "—")}</td>
                <td>${escapeHtml(byId[item.parent_class_id]?.name || "—")}</td>
                <td>${escapeHtml(item.status)}</td>
                <td>${escapeHtml(item.source)}</td>
                <td><button type="button" class="ghost small edit-class-btn" data-class-id="${item.id}">Edit</button></td>
              </tr>
            `,
          )
          .join("")}
      </tbody>
    </table>
  `;
}

function renderProperties() {
  if (!state.properties.length) {
    els.propertiesTable.innerHTML = "No ontology properties yet.";
    els.propertiesTable.classList.add("empty-state");
    return;
  }

  const classById = Object.fromEntries(state.classes.map((item) => [item.id, item]));
  els.propertiesTable.classList.remove("empty-state");
  els.propertiesTable.innerHTML = `
    <table>
      <thead>
        <tr>
          <th>ID</th>
          <th>Name</th>
          <th>Type</th>
          <th>Domain</th>
          <th>Range</th>
          <th>Status</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        ${state.properties
          .map(
            (item) => `
              <tr>
                <td>${item.id}</td>
                <td>${escapeHtml(item.name)}</td>
                <td>${escapeHtml(item.property_type)}</td>
                <td>${escapeHtml(classById[item.domain_class_id]?.name || "—")}</td>
                <td>${escapeHtml(classById[item.range_class_id]?.name || item.range_datatype || "—")}</td>
                <td>${escapeHtml(item.status)}</td>
                <td><button type="button" class="ghost small edit-property-btn" data-property-id="${item.id}">Edit</button></td>
              </tr>
            `,
          )
          .join("")}
      </tbody>
    </table>
  `;
}

function renderEntities() {
  if (!state.entities.length) {
    els.entitiesTable.innerHTML = "No entities yet.";
    els.entitiesTable.classList.add("empty-state");
    return;
  }

  const classById = Object.fromEntries(state.classes.map((item) => [item.id, item]));
  els.entitiesTable.classList.remove("empty-state");
  els.entitiesTable.innerHTML = `
    <table>
      <thead>
        <tr>
          <th>ID</th>
          <th>Name</th>
          <th>Class</th>
          <th>Aliases</th>
          <th>Source</th>
        </tr>
      </thead>
      <tbody>
        ${state.entities
          .map(
            (item) => `
              <tr>
                <td>${item.id}</td>
                <td>${escapeHtml(item.canonical_name)}</td>
                <td>${escapeHtml(classById[item.ontology_class_id]?.name || "—")}</td>
                <td>${escapeHtml((item.aliases || []).join(", ") || "—")}</td>
                <td>${escapeHtml(item.source)}</td>
              </tr>
            `,
          )
          .join("")}
      </tbody>
    </table>
  `;
}

function renderRelations() {
  if (!state.relations.length) {
    els.relationsTable.innerHTML = "No relations yet.";
    els.relationsTable.classList.add("empty-state");
    return;
  }

  const entityById = Object.fromEntries(state.entities.map((item) => [item.id, item]));
  const propertyById = Object.fromEntries(state.properties.map((item) => [item.id, item]));
  const documentById = Object.fromEntries(state.documents.map((item) => [item.id, item]));

  els.relationsTable.classList.remove("empty-state");
  els.relationsTable.innerHTML = `
    <table>
      <thead>
        <tr>
          <th>ID</th>
          <th>Subject</th>
          <th>Predicate</th>
          <th>Object</th>
          <th>Source Doc</th>
          <th>Evidence</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        ${state.relations
          .map(
            (item) => `
              <tr>
                <td>${item.id}</td>
                <td>${escapeHtml(entityById[item.subject_entity_id]?.canonical_name || `Entity #${item.subject_entity_id}`)}</td>
                <td>${escapeHtml(propertyById[item.predicate_id]?.name || `Property #${item.predicate_id}`)}</td>
                <td>${escapeHtml(entityById[item.object_entity_id]?.canonical_name || item.object_value || "—")}</td>
                <td>${escapeHtml(documentById[item.source_document_id]?.filename || "—")}</td>
                <td>${escapeHtml((item.evidence_text || "—").slice(0, 60))}</td>
                <td>
                  <div class="action-row wrap">
                    <button type="button" class="ghost small edit-relation-btn" data-relation-id="${item.id}">Edit</button>
                    <button type="button" class="ghost small view-evidence-btn" data-relation-id="${item.id}">Evidence</button>
                  </div>
                </td>
              </tr>
            `,
          )
          .join("")}
      </tbody>
    </table>
  `;
}

function renderEvidenceViewer() {
  if (!state.currentEvidence) {
    els.evidenceViewer.innerHTML = "Select a relation evidence item to inspect source text highlighting.";
    els.evidenceViewer.classList.add("empty-state");
    return;
  }

  els.evidenceViewer.classList.remove("empty-state");
  els.evidenceViewer.innerHTML = `
    <div><strong>Relation #${state.currentEvidence.relation_id}</strong></div>
    <div class="helper-text">Source document: ${escapeHtml(state.currentEvidence.source_filename || "Unknown")}</div>
    <div class="helper-text">Offsets: ${escapeHtml(state.currentEvidence.start_offset ?? "—")} - ${escapeHtml(state.currentEvidence.end_offset ?? "—")}</div>
    <div class="evidence-text">${escapeHtml(state.currentEvidence.before)}<mark>${escapeHtml(state.currentEvidence.highlight || state.currentEvidence.evidence_text || "")}</mark>${escapeHtml(state.currentEvidence.after)}</div>
  `;
}

function populateSelect(selectElement, items, formatter, includeBlank = true, blankLabel = "—") {
  const options = [];
  if (includeBlank) {
    options.push(optionMarkup("", blankLabel, true));
  }
  options.push(...items.map((item) => optionMarkup(item.id, formatter(item))));
  selectElement.innerHTML = options.join("");
}

function populateBuilderSelects() {
  populateSelect(els.classParentSelect, state.classes, (item) => item.name, true, "No parent");
  populateSelect(els.propertyDomainSelect, state.classes, (item) => item.name, true, "No domain");
  populateSelect(els.propertyRangeSelect, state.classes, (item) => item.name, true, "No range");
  populateSelect(els.entityClassSelect, state.classes, (item) => item.name, true, "Unclassified");
  populateSelect(els.relationSubjectSelect, state.entities, (item) => item.canonical_name, true, "Select subject");
  populateSelect(els.relationObjectSelect, state.entities, (item) => item.canonical_name, true, "Literal / none");
  populateSelect(els.relationPredicateSelect, state.properties, (item) => item.name, true, "Select predicate");
  populateSelect(els.relationSourceDocumentSelect, state.documents, (item) => item.filename, true, "No source document");
  togglePropertyInputs();
}

function togglePropertyInputs() {
  const isDataProperty = els.propertyType.value === "data";
  els.propertyRangeSelect.disabled = isDataProperty;
  els.propertyDatatype.disabled = !isDataProperty;
  if (!isDataProperty) {
    els.propertyDatatype.value = els.propertyDatatype.value;
  }
}

function updateStats() {
  els.classCount.textContent = state.classes.length;
  els.propertyCount.textContent = state.properties.length;
  els.entityCount.textContent = state.entities.length;
  els.relationCount.textContent = state.relations.length;
}

function polarPoint(cx, cy, radius, angle) {
  return {
    x: cx + radius * Math.cos(angle),
    y: cy + radius * Math.sin(angle),
  };
}

function createSvgElement(tag, attrs = {}) {
  const element = document.createElementNS("http://www.w3.org/2000/svg", tag);
  Object.entries(attrs).forEach(([key, value]) => element.setAttribute(key, value));
  return element;
}

function positionNodes(nodes, width, height) {
  const cx = width / 2;
  const cy = height / 2;
  const groups = {
    ontology_class: nodes.filter((node) => node.node_type === "ontology_class"),
    entity: nodes.filter((node) => node.node_type === "entity"),
    literal: nodes.filter((node) => node.node_type === "literal"),
    datatype: nodes.filter((node) => node.node_type === "datatype"),
    other: nodes.filter((node) => !["ontology_class", "entity", "literal", "datatype"].includes(node.node_type)),
  };

  const positions = {};

  const placeGroup = (groupNodes, radius, startDeg, endDeg) => {
    if (!groupNodes.length) return;
    const start = (Math.PI / 180) * startDeg;
    const end = (Math.PI / 180) * endDeg;
    groupNodes.forEach((node, index) => {
      const ratio = groupNodes.length === 1 ? 0.5 : index / (groupNodes.length - 1);
      const angle = start + (end - start) * ratio;
      positions[node.id] = polarPoint(cx, cy, radius, angle);
    });
  };

  placeGroup(groups.ontology_class, 170, 210, 330);
  placeGroup(groups.entity, 220, 30, 150);
  placeGroup(groups.literal, 120, -20, 20);
  placeGroup(groups.datatype, 120, 160, 200);
  placeGroup(groups.other, 250, 0, 360);

  return positions;
}

function renderGraph() {
  const svg = els.graphCanvas;
  svg.innerHTML = "";

  const width = 1000;
  const height = 560;

  const defs = createSvgElement("defs");
  const marker = createSvgElement("marker", {
    id: "arrowhead",
    markerWidth: "10",
    markerHeight: "7",
    refX: "9",
    refY: "3.5",
    orient: "auto",
    markerUnits: "strokeWidth",
  });
  marker.appendChild(createSvgElement("polygon", { points: "0 0, 10 3.5, 0 7", fill: "rgba(255,255,255,0.55)" }));
  defs.appendChild(marker);
  svg.appendChild(defs);

  if (!state.graph || !state.graph.nodes.length) {
    const text = createSvgElement("text", {
      x: "500",
      y: "280",
      class: "graph-label",
      "text-anchor": "middle",
    });
    text.textContent = "No graph data yet. Add ontology classes, entities, and relations to visualize the graph.";
    svg.appendChild(text);
    return;
  }

  const positions = positionNodes(state.graph.nodes, width, height);

  state.graph.edges.forEach((edge) => {
    const source = positions[edge.source];
    const target = positions[edge.target];
    if (!source || !target) return;

    const line = createSvgElement("line", {
      x1: String(source.x),
      y1: String(source.y),
      x2: String(target.x),
      y2: String(target.y),
      class: `graph-edge ${edge.edge_type}`,
      "marker-end": "url(#arrowhead)",
    });
    svg.appendChild(line);

    const label = createSvgElement("text", {
      x: String((source.x + target.x) / 2),
      y: String((source.y + target.y) / 2 - 8),
      class: "graph-label",
      "text-anchor": "middle",
    });
    label.textContent = edge.label;
    svg.appendChild(label);
  });

  state.graph.nodes.forEach((node) => {
    const position = positions[node.id];
    if (!position) return;

    const circle = createSvgElement("circle", {
      cx: String(position.x),
      cy: String(position.y),
      r: node.node_type === "ontology_class" ? "24" : node.node_type === "entity" ? "22" : "18",
      class: `graph-node ${node.node_type}`,
    });
    svg.appendChild(circle);

    const label = createSvgElement("text", {
      x: String(position.x),
      y: String(position.y),
      class: "graph-node-label",
    });
    const text = node.label.length > 16 ? `${node.label.slice(0, 15)}…` : node.label;
    label.textContent = text;
    svg.appendChild(label);
  });
}

function setClassEditMode(ontologyClass = null) {
  state.editingClassId = ontologyClass ? ontologyClass.id : null;
  els.classFormTitle.textContent = ontologyClass ? `Edit Ontology Class #${ontologyClass.id}` : "Add Ontology Class";
  els.classSubmitBtn.textContent = ontologyClass ? "Update class" : "Add class";
  els.classCancelBtn.classList.toggle("hidden", !ontologyClass);

  if (!ontologyClass) {
    els.createClassForm.reset();
    return;
  }

  els.className.value = ontologyClass.name || "";
  els.classLabel.value = ontologyClass.label || "";
  els.classDescription.value = ontologyClass.description || "";
  els.classParentSelect.value = ontologyClass.parent_class_id ? String(ontologyClass.parent_class_id) : "";
}

function setPropertyEditMode(ontologyProperty = null) {
  state.editingPropertyId = ontologyProperty ? ontologyProperty.id : null;
  els.propertyFormTitle.textContent = ontologyProperty ? `Edit Ontology Property #${ontologyProperty.id}` : "Add Ontology Property";
  els.propertySubmitBtn.textContent = ontologyProperty ? "Update property" : "Add property";
  els.propertyCancelBtn.classList.toggle("hidden", !ontologyProperty);

  if (!ontologyProperty) {
    els.createPropertyForm.reset();
    togglePropertyInputs();
    return;
  }

  els.propertyName.value = ontologyProperty.name || "";
  els.propertyLabel.value = ontologyProperty.label || "";
  els.propertyDescription.value = ontologyProperty.description || "";
  els.propertyType.value = ontologyProperty.property_type || "object";
  togglePropertyInputs();
  els.propertyDatatype.value = ontologyProperty.range_datatype || "";
  els.propertyDomainSelect.value = ontologyProperty.domain_class_id ? String(ontologyProperty.domain_class_id) : "";
  els.propertyRangeSelect.value = ontologyProperty.range_class_id ? String(ontologyProperty.range_class_id) : "";
}

function setRelationEditMode(relation = null) {
  state.editingRelationId = relation ? relation.id : null;
  els.relationFormTitle.textContent = relation ? `Edit Relation #${relation.id}` : "Add Relation";
  els.relationSubmitBtn.textContent = relation ? "Update relation" : "Add relation";
  els.relationCancelBtn.classList.toggle("hidden", !relation);

  if (!relation) {
    els.createRelationForm.reset();
    return;
  }

  els.relationSubjectSelect.value = relation.subject_entity_id ? String(relation.subject_entity_id) : "";
  els.relationPredicateSelect.value = relation.predicate_id ? String(relation.predicate_id) : "";
  els.relationObjectSelect.value = relation.object_entity_id ? String(relation.object_entity_id) : "";
  els.relationLiteralValue.value = relation.object_entity_id ? "" : relation.object_value || "";
  els.relationSourceDocumentSelect.value = relation.source_document_id ? String(relation.source_document_id) : "";
  els.relationEvidence.value = relation.evidence_text || "";
}

function restoreEditorModes() {
  const editedClass = state.editingClassId ? getClassById(state.editingClassId) : null;
  const editedProperty = state.editingPropertyId ? getPropertyById(state.editingPropertyId) : null;
  const editedRelation = state.editingRelationId ? getRelationById(state.editingRelationId) : null;
  setClassEditMode(editedClass);
  setPropertyEditMode(editedProperty);
  setRelationEditMode(editedRelation);
}

function renderAll() {
  renderProjectMeta();
  renderExtractionSummary();
  renderDocuments();
  renderCandidates();
  renderOntologyTree();
  renderClasses();
  renderProperties();
  renderEntities();
  renderRelations();
  renderEvidenceViewer();
  populateBuilderSelects();
  restoreEditorModes();
  updateStats();
  renderGraph();
}

function clearProjectState() {
  state.project = null;
  state.projectId = null;
  state.documents = [];
  state.classes = [];
  state.properties = [];
  state.entities = [];
  state.relations = [];
  state.graph = null;
  state.candidates = [];
  state.lastExtractionSummary = null;
  state.editingClassId = null;
  state.editingPropertyId = null;
  state.editingRelationId = null;
  state.currentEvidence = null;
  localStorage.removeItem(STORAGE_KEY);
  renderProjectSelect();
  renderAll();
}

async function loadGraphHealth() {
  try {
    const payload = await api("/graph/health");
    if (!payload.enabled) {
      setGraphHealthBadge("Neo4j optional", "warning");
      return;
    }
    setGraphHealthBadge(payload.connected ? "Neo4j connected" : "Neo4j unavailable", payload.connected ? "success" : "danger");
  } catch (error) {
    setGraphHealthBadge("Graph health error", "danger");
  }
}

async function loadProjects(preferredProjectId = null) {
  try {
    state.projects = await api("/api/v1/projects");
    const storedId = preferredProjectId || localStorage.getItem(STORAGE_KEY);
    const hasStored = state.projects.some((project) => String(project.id) === String(storedId));

    if (!state.projects.length) {
      clearProjectState();
      setStatus("No projects yet. Create one to start uploading documents and building ontology.", "neutral");
      return;
    }

    state.projectId = hasStored ? Number(storedId) : state.projects[0].id;
    localStorage.setItem(STORAGE_KEY, String(state.projectId));
    renderProjectSelect();
    await loadProjectData(state.projectId, false);
  } catch (error) {
    setStatus(`Unable to load projects: ${error.message}`, "danger");
  }
}

async function loadProjectData(projectId, announce = true) {
  if (!projectId) {
    clearProjectState();
    return;
  }

  try {
    const [project, documents, classes, properties, entities, relations, graph] = await Promise.all([
      api(`/api/v1/projects/${projectId}`),
      api(`/api/v1/projects/${projectId}/documents`),
      api(`/api/v1/projects/${projectId}/ontology/classes`),
      api(`/api/v1/projects/${projectId}/ontology/properties`),
      api(`/api/v1/projects/${projectId}/kg/entities`),
      api(`/api/v1/projects/${projectId}/kg/relations`),
      api(`/api/v1/projects/${projectId}/graph/view`),
    ]);

    state.projectId = Number(projectId);
    state.project = project;
    state.documents = documents;
    state.classes = classes;
    state.properties = properties;
    state.entities = entities;
    state.relations = relations;
    state.graph = graph;
    renderProjectSelect();
    renderAll();
    localStorage.setItem(STORAGE_KEY, String(projectId));

    if (announce) {
      setStatus(`Loaded project '${project.name}'.`, "success");
    }
  } catch (error) {
    setStatus(`Unable to load project data: ${error.message}`, "danger");
  }
}

async function loadRelationEvidence(relationId) {
  const projectId = requireProject();
  if (!projectId) return;
  try {
    state.currentEvidence = await api(`/api/v1/projects/${projectId}/kg/relations/${relationId}/evidence`);
    renderEvidenceViewer();
    setStatus(`Loaded evidence for relation #${relationId}.`, "success");
  } catch (error) {
    setStatus(`Could not load evidence: ${error.message}`, "danger");
  }
}

els.createProjectForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const payload = {
      name: els.projectName.value.trim(),
      description: els.projectDescription.value.trim() || null,
    };
    const project = await api("/api/v1/projects", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    els.createProjectForm.reset();
    setStatus(`Created project '${project.name}'.`, "success");
    await loadProjects(project.id);
  } catch (error) {
    setStatus(`Project creation failed: ${error.message}`, "danger");
  }
});

els.projectSelect.addEventListener("change", async () => {
  const projectId = Number(els.projectSelect.value || 0);
  if (!projectId) {
    clearProjectState();
    return;
  }
  state.lastExtractionSummary = null;
  state.currentEvidence = null;
  await loadProjectData(projectId);
});

els.refreshProjectsBtn.addEventListener("click", async () => {
  await loadProjects(state.projectId);
  setStatus("Project list refreshed.", "success");
});

els.reloadWorkspaceBtn.addEventListener("click", async () => {
  if (!requireProject()) return;
  await loadProjectData(state.projectId);
});

els.syncGraphBtn.addEventListener("click", async () => {
  const projectId = requireProject();
  if (!projectId) return;

  try {
    const result = await api(`/api/v1/projects/${projectId}/graph/sync`, { method: "POST" });
    setStatus(result.message, result.synced ? "success" : "warning");
    await loadGraphHealth();
  } catch (error) {
    setStatus(`Graph sync failed: ${error.message}`, "danger");
  }
});

els.exportRdfBtn.addEventListener("click", async () => {
  const projectId = requireProject();
  if (!projectId) return;
  try {
    await downloadFile(`/api/v1/projects/${projectId}/export/rdf`, `project_${projectId}.rdf`);
    setStatus("RDF export downloaded.", "success");
  } catch (error) {
    setStatus(`RDF export failed: ${error.message}`, "danger");
  }
});

els.exportOwlBtn.addEventListener("click", async () => {
  const projectId = requireProject();
  if (!projectId) return;
  try {
    await downloadFile(`/api/v1/projects/${projectId}/export/owl`, `project_${projectId}.owl`);
    setStatus("OWL export downloaded.", "success");
  } catch (error) {
    setStatus(`OWL export failed: ${error.message}`, "danger");
  }
});

els.exportJsonldBtn.addEventListener("click", async () => {
  const projectId = requireProject();
  if (!projectId) return;
  try {
    await downloadFile(`/api/v1/projects/${projectId}/export/jsonld`, `project_${projectId}.jsonld`);
    setStatus("JSON-LD export downloaded.", "success");
  } catch (error) {
    setStatus(`JSON-LD export failed: ${error.message}`, "danger");
  }
});

els.exportTurtleBtn.addEventListener("click", async () => {
  const projectId = requireProject();
  if (!projectId) return;
  try {
    await downloadFile(`/api/v1/projects/${projectId}/export/turtle`, `project_${projectId}.ttl`);
    setStatus("Turtle export downloaded.", "success");
  } catch (error) {
    setStatus(`Turtle export failed: ${error.message}`, "danger");
  }
});

els.uploadDocumentForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const projectId = requireProject();
  if (!projectId) return;
  if (!els.documentFile.files.length) {
    setStatus("Choose a document file to upload.", "warning");
    return;
  }

  try {
    const formData = new FormData();
    formData.append("file", els.documentFile.files[0]);
    const result = await api(`/api/v1/projects/${projectId}/documents?auto_extract=true`, {
      method: "POST",
      body: formData,
    });
    els.uploadDocumentForm.reset();
    state.lastExtractionSummary = result.extraction || null;
    const extractionMsg = result.extraction
      ? ` and extracted ${result.extraction.created_relations} relations`
      : "";
    const ontologyMsg = result.ontology
      ? ` and generated ${result.ontology.candidates.length} class candidates`
      : "";
    const message = `Uploaded '${result.document.filename}'${extractionMsg}${ontologyMsg}.`;
    setStatus(message, "success");
    await loadProjectData(projectId, false);
  } catch (error) {
    setStatus(`Document upload failed: ${error.message}`, "danger");
  }
});

els.uploadOntologyForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const projectId = requireProject();
  if (!projectId) return;
  if (!els.ontologyFile.files.length) {
    setStatus("Choose an ontology file to upload.", "warning");
    return;
  }

  try {
    const formData = new FormData();
    formData.append("file", els.ontologyFile.files[0]);
    const result = await api(`/api/v1/projects/${projectId}/ontology/import`, {
      method: "POST",
      body: formData,
    });
    els.uploadOntologyForm.reset();
    setStatus(result.message, "success");
    activateTab("ontology");
    await loadProjectData(projectId, false);
  } catch (error) {
    setStatus(`Ontology import failed: ${error.message}`, "danger");
  }
});

els.runExtractionBtn.addEventListener("click", async () => {
  const projectId = requireProject();
  if (!projectId) return;

  try {
    const result = await api(`/api/v1/projects/${projectId}/kg/extract`, { method: "POST" });
    state.lastExtractionSummary = result;
    await loadProjectData(projectId, false);
    activateTab("kg");
    setStatus(result.message, "success");
  } catch (error) {
    setStatus(`KG extraction failed: ${error.message}`, "danger");
  }
});

els.generateCandidatesBtn.addEventListener("click", async () => {
  const projectId = requireProject();
  if (!projectId) return;

  try {
    const payload = {
      max_candidates: Number(els.candidateLimit.value || 12),
      min_term_length: Number(els.candidateTermLength.value || 4),
    };
    const result = await api(`/api/v1/projects/${projectId}/ontology/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    state.candidates = result.candidates || [];
    renderCandidates();
    setStatus(`Generated ${state.candidates.length} ontology candidates from uploaded documents.`, "success");
  } catch (error) {
    state.candidates = [];
    renderCandidates();
    setStatus(`Candidate generation failed: ${error.message}`, "danger");
  }
});

els.candidateResults.addEventListener("click", async (event) => {
  const target = event.target.closest(".add-candidate-btn");
  if (!target) return;

  try {
    const projectId = requireProject();
    if (!projectId) return;
    const term = target.dataset.term;
    await api(`/api/v1/projects/${projectId}/ontology/classes`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: term,
        label: titleCase(term),
        description: `Imported from document suggestion: ${term}`,
        parent_class_id: null,
        status: "draft",
        source: "candidate",
        confidence: null,
      }),
    });
    await loadProjectData(projectId, false);
    setStatus(`Added '${term}' as ontology class.`, "success");
    activateTab("ontology");
  } catch (error) {
    setStatus(`Could not add candidate as class: ${error.message}`, "danger");
  }
});

els.createClassForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const projectId = requireProject();
  if (!projectId) return;

  try {
    const payload = {
      name: els.className.value.trim(),
      label: els.classLabel.value.trim() || null,
      description: els.classDescription.value.trim() || null,
      parent_class_id: els.classParentSelect.value ? Number(els.classParentSelect.value) : null,
      status: "draft",
      source: state.editingClassId ? undefined : "manual",
      confidence: null,
    };

    if (state.editingClassId) {
      delete payload.source;
      await api(`/api/v1/projects/${projectId}/ontology/classes/${state.editingClassId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      setStatus("Ontology class updated successfully.", "success");
    } else {
      await api(`/api/v1/projects/${projectId}/ontology/classes`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      setStatus("Ontology class added successfully.", "success");
    }

    setClassEditMode(null);
    await loadProjectData(projectId, false);
  } catch (error) {
    setStatus(`Could not save ontology class: ${error.message}`, "danger");
  }
});

els.classCancelBtn.addEventListener("click", () => setClassEditMode(null));

els.propertyType.addEventListener("change", togglePropertyInputs);

els.createPropertyForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const projectId = requireProject();
  if (!projectId) return;

  try {
    const propertyType = els.propertyType.value;
    const payload = {
      name: els.propertyName.value.trim(),
      label: els.propertyLabel.value.trim() || null,
      description: els.propertyDescription.value.trim() || null,
      property_type: propertyType,
      domain_class_id: els.propertyDomainSelect.value ? Number(els.propertyDomainSelect.value) : null,
      range_class_id: propertyType === "object" && els.propertyRangeSelect.value ? Number(els.propertyRangeSelect.value) : null,
      range_datatype: propertyType === "data" ? els.propertyDatatype.value.trim() || null : null,
      status: "draft",
      confidence: null,
    };

    if (state.editingPropertyId) {
      await api(`/api/v1/projects/${projectId}/ontology/properties/${state.editingPropertyId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      setStatus("Ontology property updated successfully.", "success");
    } else {
      await api(`/api/v1/projects/${projectId}/ontology/properties`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      setStatus("Ontology property added successfully.", "success");
    }

    setPropertyEditMode(null);
    await loadProjectData(projectId, false);
  } catch (error) {
    setStatus(`Could not save ontology property: ${error.message}`, "danger");
  }
});

els.propertyCancelBtn.addEventListener("click", () => setPropertyEditMode(null));

els.createEntityForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const projectId = requireProject();
  if (!projectId) return;

  try {
    const payload = {
      canonical_name: els.entityName.value.trim(),
      ontology_class_id: els.entityClassSelect.value ? Number(els.entityClassSelect.value) : null,
      aliases: els.entityAliases.value
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean),
      source: "manual",
      confidence: null,
    };

    await api(`/api/v1/projects/${projectId}/kg/entities`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    els.createEntityForm.reset();
    await loadProjectData(projectId, false);
    setStatus("Entity added successfully.", "success");
  } catch (error) {
    setStatus(`Could not create entity: ${error.message}`, "danger");
  }
});

els.createRelationForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const projectId = requireProject();
  if (!projectId) return;

  try {
    const objectEntityId = els.relationObjectSelect.value ? Number(els.relationObjectSelect.value) : null;
    const literalValue = els.relationLiteralValue.value.trim() || null;

    if (!objectEntityId && !literalValue) {
      throw new Error("Provide either an object entity or a literal value for the relation.");
    }

    const payload = {
      subject_entity_id: Number(els.relationSubjectSelect.value),
      predicate_id: Number(els.relationPredicateSelect.value),
      object_entity_id: objectEntityId,
      object_value: objectEntityId ? null : literalValue,
      evidence_text: els.relationEvidence.value.trim() || null,
      source_document_id: els.relationSourceDocumentSelect.value ? Number(els.relationSourceDocumentSelect.value) : null,
      confidence: null,
    };

    if (state.editingRelationId) {
      await api(`/api/v1/projects/${projectId}/kg/relations/${state.editingRelationId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      setStatus("Relation updated successfully.", "success");
    } else {
      await api(`/api/v1/projects/${projectId}/kg/relations`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      setStatus("Relation added successfully.", "success");
    }

    setRelationEditMode(null);
    await loadProjectData(projectId, false);
  } catch (error) {
    setStatus(`Could not save relation: ${error.message}`, "danger");
  }
});

els.relationCancelBtn.addEventListener("click", () => setRelationEditMode(null));

els.ontologyTree.addEventListener("click", (event) => {
  const button = event.target.closest(".edit-class-btn");
  if (!button) return;
  const ontologyClass = getClassById(button.dataset.classId);
  if (!ontologyClass) return;
  activateTab("ontology");
  setClassEditMode(ontologyClass);
});

els.classesTable.addEventListener("click", (event) => {
  const button = event.target.closest(".edit-class-btn");
  if (!button) return;
  const ontologyClass = getClassById(button.dataset.classId);
  if (!ontologyClass) return;
  activateTab("ontology");
  setClassEditMode(ontologyClass);
});

els.propertiesTable.addEventListener("click", (event) => {
  const button = event.target.closest(".edit-property-btn");
  if (!button) return;
  const ontologyProperty = getPropertyById(button.dataset.propertyId);
  if (!ontologyProperty) return;
  activateTab("ontology");
  setPropertyEditMode(ontologyProperty);
});

els.relationsTable.addEventListener("click", async (event) => {
  const editButton = event.target.closest(".edit-relation-btn");
  if (editButton) {
    const relation = getRelationById(editButton.dataset.relationId);
    if (!relation) return;
    activateTab("kg");
    setRelationEditMode(relation);
    return;
  }

  const evidenceButton = event.target.closest(".view-evidence-btn");
  if (evidenceButton) {
    activateTab("kg");
    await loadRelationEvidence(Number(evidenceButton.dataset.relationId));
  }
});

els.tabs.forEach((tab) => {
  tab.addEventListener("click", () => activateTab(tab.dataset.tab));
});

async function init() {
  togglePropertyInputs();
  setClassEditMode(null);
  setPropertyEditMode(null);
  setRelationEditMode(null);
  activateTab("ingest");
  await loadGraphHealth();
  await loadProjects();
}

init();
