/**
 * Sistema de Impressao de Etiquetas - Frontend
 */

// Estado da aplicacao
const state = {
    clientes: [],
    impressoras: [],
    tiposEtiqueta: [],
    clienteSelecionado: null,
    enderecoSelecionado: null
};

// API Helper
const api = {
    async get(url) {
        const response = await fetch(url);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        return response.json();
    },

    async post(url, data) {
        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Erro na requisicao');
        }
        return response.json();
    },

    async put(url, data) {
        const response = await fetch(url, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Erro na requisicao');
        }
        return response.json();
    },

    async delete(url) {
        const response = await fetch(url, { method: 'DELETE' });
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        return response.json();
    }
};

// Toast Notification
function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${type} show`;
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

// Tab Navigation
function initTabs() {
    const tabs = document.querySelectorAll('.tab-btn');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            // Remove active de todas as tabs
            tabs.forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

            // Ativa a tab clicada
            tab.classList.add('active');
            document.getElementById(`tab-${tab.dataset.tab}`).classList.add('active');
        });
    });
}

// Modal Helper
function openModal(modalId) {
    document.getElementById(modalId).classList.add('show');
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('show');
}

function initModals() {
    // Fechar ao clicar no X ou no botao cancelar
    document.querySelectorAll('.modal-close, .modal-cancel').forEach(el => {
        el.addEventListener('click', (e) => {
            e.target.closest('.modal').classList.remove('show');
        });
    });

    // Fechar ao clicar fora
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.remove('show');
            }
        });
    });
}

// ============== Clientes ==============

async function carregarClientes() {
    try {
        state.clientes = await api.get('/api/clientes');
        renderizarClientes();
        atualizarSelectClientes();
    } catch (error) {
        showToast('Erro ao carregar clientes', 'error');
        console.error(error);
    }
}

function renderizarClientes() {
    const tbody = document.getElementById('lista-clientes');

    if (state.clientes.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="empty-state"><p>Nenhum cliente cadastrado</p></td></tr>';
        return;
    }

    tbody.innerHTML = state.clientes.map(cliente => `
        <tr>
            <td>${cliente.nome}</td>
            <td>${cliente.documento || '-'}</td>
            <td>${cliente.telefone || '-'}</td>
            <td>${cliente.email || '-'}</td>
            <td>${cliente.qtd_enderecos}</td>
            <td class="actions">
                <button class="btn btn-sm btn-secondary" onclick="editarCliente(${cliente.id})">Editar</button>
                <button class="btn btn-sm btn-danger" onclick="excluirCliente(${cliente.id})">Excluir</button>
            </td>
        </tr>
    `).join('');
}

function atualizarSelectClientes() {
    const select = document.getElementById('select-cliente');
    select.innerHTML = '<option value="">-- Selecione um cliente --</option>';
    state.clientes.forEach(cliente => {
        select.innerHTML += `<option value="${cliente.id}">${cliente.nome}</option>`;
    });
}

async function editarCliente(id) {
    try {
        const cliente = await api.get(`/api/clientes/${id}`);

        document.getElementById('modal-cliente-titulo').textContent = 'Editar Cliente';
        document.getElementById('cliente-id').value = cliente.id;
        document.getElementById('cliente-nome').value = cliente.nome;
        document.getElementById('cliente-documento').value = cliente.documento || '';
        document.getElementById('cliente-telefone').value = cliente.telefone || '';
        document.getElementById('cliente-email').value = cliente.email || '';
        document.getElementById('cliente-observacoes').value = cliente.observacoes || '';

        // Renderizar enderecos
        renderizarEnderecosForm(cliente.enderecos);

        openModal('modal-cliente');
    } catch (error) {
        showToast('Erro ao carregar cliente', 'error');
        console.error(error);
    }
}

async function excluirCliente(id) {
    if (!confirm('Deseja realmente excluir este cliente?')) return;

    try {
        await api.delete(`/api/clientes/${id}`);
        showToast('Cliente excluido com sucesso', 'success');
        carregarClientes();
    } catch (error) {
        showToast('Erro ao excluir cliente', 'error');
        console.error(error);
    }
}

function novoCliente() {
    document.getElementById('modal-cliente-titulo').textContent = 'Novo Cliente';
    document.getElementById('form-cliente').reset();
    document.getElementById('cliente-id').value = '';
    document.getElementById('lista-enderecos-form').innerHTML = '';
    openModal('modal-cliente');
}

function renderizarEnderecosForm(enderecos = []) {
    const container = document.getElementById('lista-enderecos-form');
    container.innerHTML = enderecos.map((end, index) => criarEnderecoFormHTML(end, index)).join('');
}

function criarEnderecoFormHTML(endereco = {}, index = 0) {
    return `
        <div class="endereco-form-item" data-index="${index}" data-id="${endereco.id || ''}">
            <button type="button" class="btn btn-sm btn-danger btn-remove-endereco" onclick="removerEnderecoForm(this)">X</button>
            <div class="form-row">
                <div class="form-group">
                    <label>Descricao:</label>
                    <input type="text" class="form-control end-descricao" value="${endereco.descricao || ''}" placeholder="Ex: Residencial">
                </div>
                <div class="form-group">
                    <label>Destinatario:</label>
                    <input type="text" class="form-control end-destinatario" value="${endereco.destinatario || ''}" placeholder="Se diferente do cliente">
                </div>
            </div>
            <div class="form-row">
                <div class="form-group flex-2">
                    <label>Logradouro:</label>
                    <input type="text" class="form-control end-logradouro" value="${endereco.logradouro || ''}" required>
                </div>
                <div class="form-group">
                    <label>Numero:</label>
                    <input type="text" class="form-control end-numero" value="${endereco.numero || ''}" required>
                </div>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Complemento:</label>
                    <input type="text" class="form-control end-complemento" value="${endereco.complemento || ''}">
                </div>
                <div class="form-group">
                    <label>Bairro:</label>
                    <input type="text" class="form-control end-bairro" value="${endereco.bairro || ''}" required>
                </div>
            </div>
            <div class="form-row">
                <div class="form-group flex-2">
                    <label>Cidade:</label>
                    <input type="text" class="form-control end-cidade" value="${endereco.cidade || ''}" required>
                </div>
                <div class="form-group">
                    <label>Estado:</label>
                    <select class="form-control end-estado" required>
                        <option value="">UF</option>
                        ${['AC','AL','AP','AM','BA','CE','DF','ES','GO','MA','MT','MS','MG','PA','PB','PR','PE','PI','RJ','RN','RS','RO','RR','SC','SP','SE','TO']
                            .map(uf => `<option value="${uf}" ${endereco.estado === uf ? 'selected' : ''}>${uf}</option>`).join('')}
                    </select>
                </div>
                <div class="form-group">
                    <label>CEP:</label>
                    <input type="text" class="form-control end-cep" value="${endereco.cep || ''}" placeholder="00000-000" required>
                </div>
            </div>
            <div class="form-group checkbox-group">
                <label>
                    <input type="checkbox" class="end-principal" ${endereco.principal ? 'checked' : ''}>
                    Endereco principal
                </label>
            </div>
        </div>
    `;
}

function adicionarEnderecoForm() {
    const container = document.getElementById('lista-enderecos-form');
    const index = container.children.length;
    container.insertAdjacentHTML('beforeend', criarEnderecoFormHTML({}, index));
}

function removerEnderecoForm(btn) {
    btn.closest('.endereco-form-item').remove();
}

function coletarEnderecosForm() {
    const items = document.querySelectorAll('.endereco-form-item');
    return Array.from(items).map(item => ({
        id: item.dataset.id || null,
        descricao: item.querySelector('.end-descricao').value,
        destinatario: item.querySelector('.end-destinatario').value,
        logradouro: item.querySelector('.end-logradouro').value,
        numero: item.querySelector('.end-numero').value,
        complemento: item.querySelector('.end-complemento').value,
        bairro: item.querySelector('.end-bairro').value,
        cidade: item.querySelector('.end-cidade').value,
        estado: item.querySelector('.end-estado').value,
        cep: item.querySelector('.end-cep').value,
        principal: item.querySelector('.end-principal').checked
    }));
}

async function salvarCliente(e) {
    e.preventDefault();

    const clienteId = document.getElementById('cliente-id').value;
    const dados = {
        nome: document.getElementById('cliente-nome').value,
        documento: document.getElementById('cliente-documento').value,
        telefone: document.getElementById('cliente-telefone').value,
        email: document.getElementById('cliente-email').value,
        observacoes: document.getElementById('cliente-observacoes').value
    };

    try {
        if (clienteId) {
            // Atualizar cliente
            await api.put(`/api/clientes/${clienteId}`, dados);

            // Atualizar/criar enderecos
            const enderecos = coletarEnderecosForm();
            for (const end of enderecos) {
                if (end.id) {
                    await api.put(`/api/enderecos/${end.id}`, end);
                } else {
                    await api.post(`/api/clientes/${clienteId}/enderecos`, end);
                }
            }

            showToast('Cliente atualizado com sucesso', 'success');
        } else {
            // Criar cliente com enderecos
            dados.enderecos = coletarEnderecosForm();
            await api.post('/api/clientes', dados);
            showToast('Cliente criado com sucesso', 'success');
        }

        closeModal('modal-cliente');
        carregarClientes();
    } catch (error) {
        showToast(error.message || 'Erro ao salvar cliente', 'error');
        console.error(error);
    }
}

// ============== Impressoras ==============

async function carregarImpressoras() {
    try {
        state.impressoras = await api.get('/api/impressoras');
        renderizarImpressoras();
        atualizarSelectImpressoras();
    } catch (error) {
        showToast('Erro ao carregar impressoras', 'error');
        console.error(error);
    }
}

function renderizarImpressoras() {
    const tbody = document.getElementById('lista-impressoras');

    if (state.impressoras.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="empty-state"><p>Nenhuma impressora cadastrada</p></td></tr>';
        return;
    }

    tbody.innerHTML = state.impressoras.map(imp => `
        <tr>
            <td>${imp.nome}</td>
            <td>${imp.nome_sistema}</td>
            <td>${imp.tipo}</td>
            <td>${imp.modelo || '-'}</td>
            <td><span class="status-badge ${imp.ativa ? 'enabled' : 'disabled'}">${imp.ativa ? 'Ativa' : 'Inativa'}</span></td>
            <td class="actions">
                <button class="btn btn-sm btn-info" onclick="testarImpressora(${imp.id})">Testar</button>
                <button class="btn btn-sm btn-secondary" onclick="editarImpressora(${imp.id})">Editar</button>
                <button class="btn btn-sm btn-danger" onclick="excluirImpressora(${imp.id})">Excluir</button>
            </td>
        </tr>
    `).join('');
}

function atualizarSelectImpressoras() {
    const select = document.getElementById('select-impressora');
    select.innerHTML = '<option value="">-- Usar padrao configurada --</option>';
    state.impressoras.forEach(imp => {
        select.innerHTML += `<option value="${imp.id}">${imp.nome}</option>`;
    });
}

async function testarImpressora(id) {
    try {
        const result = await api.get(`/api/impressoras/${id}/testar`);
        showToast(result.message, result.success ? 'success' : 'error');
    } catch (error) {
        showToast('Erro ao testar impressora', 'error');
    }
}

function novaImpressora() {
    document.getElementById('modal-impressora-titulo').textContent = 'Nova Impressora';
    document.getElementById('form-impressora').reset();
    document.getElementById('impressora-id').value = '';
    openModal('modal-impressora');
}

function editarImpressora(id) {
    const impressora = state.impressoras.find(i => i.id === id);
    if (!impressora) return;

    document.getElementById('modal-impressora-titulo').textContent = 'Editar Impressora';
    document.getElementById('impressora-id').value = impressora.id;
    document.getElementById('impressora-nome').value = impressora.nome;
    document.getElementById('impressora-nome-sistema').value = impressora.nome_sistema;
    document.getElementById('impressora-tipo').value = impressora.tipo;
    document.getElementById('impressora-modelo').value = impressora.modelo || '';
    document.getElementById('impressora-localizacao').value = impressora.localizacao || '';
    openModal('modal-impressora');
}

async function excluirImpressora(id) {
    if (!confirm('Deseja realmente excluir esta impressora?')) return;

    try {
        await api.delete(`/api/impressoras/${id}`);
        showToast('Impressora excluida com sucesso', 'success');
        carregarImpressoras();
    } catch (error) {
        showToast('Erro ao excluir impressora', 'error');
    }
}

async function salvarImpressora(e) {
    e.preventDefault();

    const impressoraId = document.getElementById('impressora-id').value;
    const dados = {
        nome: document.getElementById('impressora-nome').value,
        nome_sistema: document.getElementById('impressora-nome-sistema').value,
        tipo: document.getElementById('impressora-tipo').value,
        modelo: document.getElementById('impressora-modelo').value,
        localizacao: document.getElementById('impressora-localizacao').value
    };

    try {
        if (impressoraId) {
            await api.put(`/api/impressoras/${impressoraId}`, dados);
            showToast('Impressora atualizada com sucesso', 'success');
        } else {
            await api.post('/api/impressoras', dados);
            showToast('Impressora criada com sucesso', 'success');
        }

        closeModal('modal-impressora');
        carregarImpressoras();
    } catch (error) {
        showToast(error.message || 'Erro ao salvar impressora', 'error');
    }
}

async function detectarImpressorasSistema() {
    try {
        const impressoras = await api.get('/api/impressoras/sistema');
        const container = document.getElementById('lista-impressoras-sistema');

        if (impressoras.length === 0) {
            container.innerHTML = '<p class="empty-state">Nenhuma impressora detectada no sistema</p>';
        } else {
            container.innerHTML = impressoras.map(imp => `
                <div class="impressora-sistema-item">
                    <div class="impressora-sistema-info">
                        <h4>${imp.name}</h4>
                        <span class="status-badge ${imp.enabled ? 'enabled' : 'disabled'}">
                            ${imp.enabled ? 'Habilitada' : 'Desabilitada'}
                        </span>
                        ${imp.is_default ? '<span class="status-badge enabled">Padrao</span>' : ''}
                    </div>
                    <button class="btn btn-sm btn-primary" onclick="adicionarImpressoraSistema('${imp.name}')">
                        Adicionar
                    </button>
                </div>
            `).join('');
        }

        openModal('modal-impressoras-sistema');
    } catch (error) {
        showToast('Erro ao detectar impressoras', 'error');
    }
}

function adicionarImpressoraSistema(nome) {
    document.getElementById('impressora-nome').value = nome;
    document.getElementById('impressora-nome-sistema').value = nome;
    document.getElementById('impressora-id').value = '';
    document.getElementById('modal-impressora-titulo').textContent = 'Nova Impressora';
    closeModal('modal-impressoras-sistema');
    openModal('modal-impressora');
}

// ============== Tipos de Etiqueta e Configuracoes ==============

async function carregarTiposEtiqueta() {
    try {
        state.tiposEtiqueta = await api.get('/api/tipos-etiqueta');
        atualizarSelectTiposEtiqueta();
        carregarConfiguracoes();
    } catch (error) {
        showToast('Erro ao carregar tipos de etiqueta', 'error');
    }
}

function atualizarSelectTiposEtiqueta() {
    const select = document.getElementById('select-tipo-etiqueta');
    select.innerHTML = '<option value="">-- Selecione o tipo --</option>';
    state.tiposEtiqueta.forEach(tipo => {
        select.innerHTML += `<option value="${tipo.id}">${tipo.name}</option>`;
    });
}

async function carregarConfiguracoes() {
    try {
        const configs = await api.get('/api/configuracoes-etiqueta');
        const container = document.getElementById('config-etiquetas');

        container.innerHTML = state.tiposEtiqueta.map(tipo => {
            const config = configs.find(c => c.tipo_etiqueta === tipo.id);
            return `
                <div class="config-item">
                    <label>${tipo.name}:</label>
                    <select class="form-control" onchange="salvarConfiguracao('${tipo.id}', this.value)">
                        <option value="">-- Nenhuma --</option>
                        ${state.impressoras.map(imp => `
                            <option value="${imp.id}" ${config && config.impressora_id === imp.id ? 'selected' : ''}>
                                ${imp.nome}
                            </option>
                        `).join('')}
                    </select>
                </div>
            `;
        }).join('');
    } catch (error) {
        console.error(error);
    }
}

async function salvarConfiguracao(tipoEtiqueta, impressoraId) {
    try {
        await api.put(`/api/configuracoes-etiqueta/${tipoEtiqueta}?impressora_id=${impressoraId || ''}`);
        showToast('Configuracao salva', 'success');
    } catch (error) {
        showToast('Erro ao salvar configuracao', 'error');
    }
}

// ============== Remetente ==============

async function carregarRemetente() {
    try {
        const remetente = await api.get('/api/remetente');
        if (remetente) {
            document.getElementById('rem-nome').value = remetente.nome || '';
            document.getElementById('rem-logradouro').value = remetente.logradouro || '';
            document.getElementById('rem-numero').value = remetente.numero || '';
            document.getElementById('rem-complemento').value = remetente.complemento || '';
            document.getElementById('rem-bairro').value = remetente.bairro || '';
            document.getElementById('rem-cidade').value = remetente.cidade || '';
            document.getElementById('rem-estado').value = remetente.estado || '';
            document.getElementById('rem-cep').value = remetente.cep || '';
        }
    } catch (error) {
        console.error(error);
    }
}

async function salvarRemetente(e) {
    e.preventDefault();

    const dados = {
        nome: document.getElementById('rem-nome').value,
        logradouro: document.getElementById('rem-logradouro').value,
        numero: document.getElementById('rem-numero').value,
        complemento: document.getElementById('rem-complemento').value,
        bairro: document.getElementById('rem-bairro').value,
        cidade: document.getElementById('rem-cidade').value,
        estado: document.getElementById('rem-estado').value,
        cep: document.getElementById('rem-cep').value
    };

    try {
        await api.post('/api/remetente', dados);
        showToast('Remetente salvo com sucesso', 'success');
    } catch (error) {
        showToast('Erro ao salvar remetente', 'error');
    }
}

// ============== Impressao ==============

async function carregarEnderecos(clienteId) {
    try {
        const enderecos = await api.get(`/api/clientes/${clienteId}/enderecos`);
        const select = document.getElementById('select-endereco');
        select.innerHTML = '<option value="">-- Selecione um endereco --</option>';

        enderecos.forEach(end => {
            const descricao = end.descricao ? `(${end.descricao}) ` : '';
            select.innerHTML += `<option value="${end.id}">${descricao}${end.logradouro}, ${end.numero} - ${end.cidade}/${end.estado}</option>`;
        });

        select.disabled = false;
        state.clienteSelecionado = await api.get(`/api/clientes/${clienteId}`);
    } catch (error) {
        showToast('Erro ao carregar enderecos', 'error');
    }
}

function exibirEndereco(enderecoId) {
    if (!state.clienteSelecionado) return;

    const endereco = state.clienteSelecionado.enderecos.find(e => e.id == enderecoId);
    if (!endereco) {
        document.getElementById('endereco-preview').style.display = 'none';
        state.enderecoSelecionado = null;
        atualizarBotoes();
        return;
    }

    state.enderecoSelecionado = endereco;
    const cep = endereco.cep.includes('-') ? endereco.cep : `${endereco.cep.substring(0, 5)}-${endereco.cep.substring(5)}`;

    document.getElementById('endereco-detalhes').innerHTML = `
        <strong>${endereco.destinatario || state.clienteSelecionado.nome}</strong><br>
        ${endereco.logradouro}, ${endereco.numero}${endereco.complemento ? ` - ${endereco.complemento}` : ''}<br>
        ${endereco.bairro}<br>
        <strong>${cep}</strong> - ${endereco.cidade}/${endereco.estado}
    `;

    document.getElementById('endereco-preview').style.display = 'block';
    atualizarBotoes();
}

function atualizarBotoes() {
    const temCliente = state.clienteSelecionado !== null;
    const temEndereco = state.enderecoSelecionado !== null;
    const temTipo = document.getElementById('select-tipo-etiqueta').value !== '';

    const habilitar = temCliente && temEndereco && temTipo;
    document.getElementById('btn-preview').disabled = !habilitar;
    document.getElementById('btn-download').disabled = !habilitar;
    document.getElementById('btn-imprimir').disabled = !habilitar;
}

async function gerarPreview() {
    const dados = {
        cliente_id: state.clienteSelecionado.id,
        endereco_id: state.enderecoSelecionado.id,
        tipo_etiqueta: document.getElementById('select-tipo-etiqueta').value,
        incluir_codigo_barras: document.getElementById('incluir-barcode').checked,
        incluir_remetente: document.getElementById('incluir-remetente').checked
    };

    try {
        const response = await fetch('/api/preview', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(dados)
        });

        if (!response.ok) throw new Error('Erro ao gerar preview');

        const blob = await response.blob();
        const url = URL.createObjectURL(blob);

        document.getElementById('preview-iframe').src = url;
        document.getElementById('preview-container').style.display = 'block';
    } catch (error) {
        showToast('Erro ao gerar preview', 'error');
    }
}

async function downloadEtiqueta() {
    const dados = {
        cliente_id: state.clienteSelecionado.id,
        endereco_id: state.enderecoSelecionado.id,
        tipo_etiqueta: document.getElementById('select-tipo-etiqueta').value,
        incluir_codigo_barras: document.getElementById('incluir-barcode').checked,
        incluir_remetente: document.getElementById('incluir-remetente').checked
    };

    try {
        const response = await fetch('/api/download', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(dados)
        });

        if (!response.ok) throw new Error('Erro ao gerar download');

        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `etiqueta_${state.clienteSelecionado.nome.replace(/ /g, '_')}.pdf`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    } catch (error) {
        showToast('Erro ao fazer download', 'error');
    }
}

async function imprimir() {
    const impressoraId = document.getElementById('select-impressora').value;
    const dados = {
        cliente_id: state.clienteSelecionado.id,
        endereco_id: state.enderecoSelecionado.id,
        tipo_etiqueta: document.getElementById('select-tipo-etiqueta').value,
        quantidade: parseInt(document.getElementById('quantidade').value) || 1,
        impressora_id: impressoraId ? parseInt(impressoraId) : null,
        incluir_codigo_barras: document.getElementById('incluir-barcode').checked,
        incluir_remetente: document.getElementById('incluir-remetente').checked
    };

    try {
        const result = await api.post('/api/imprimir', dados);
        showToast('Etiqueta enviada para impressao!', 'success');
    } catch (error) {
        showToast(error.message || 'Erro ao imprimir', 'error');
    }
}

// ============== Busca de Clientes ==============

let buscaTimeout = null;

function initBuscaClientes() {
    const input = document.getElementById('busca-cliente');
    input.addEventListener('input', (e) => {
        clearTimeout(buscaTimeout);
        buscaTimeout = setTimeout(() => {
            buscarClientes(e.target.value);
        }, 300);
    });
}

async function buscarClientes(termo) {
    try {
        const url = termo ? `/api/clientes?search=${encodeURIComponent(termo)}` : '/api/clientes';
        state.clientes = await api.get(url);
        renderizarClientes();
    } catch (error) {
        console.error(error);
    }
}

// ============== Event Listeners ==============

function initEventListeners() {
    // Tabs
    initTabs();

    // Modals
    initModals();

    // Forms
    document.getElementById('form-cliente').addEventListener('submit', salvarCliente);
    document.getElementById('form-impressora').addEventListener('submit', salvarImpressora);
    document.getElementById('form-remetente').addEventListener('submit', salvarRemetente);

    // Botoes
    document.getElementById('btn-novo-cliente').addEventListener('click', novoCliente);
    document.getElementById('btn-add-endereco').addEventListener('click', adicionarEnderecoForm);
    document.getElementById('btn-nova-impressora').addEventListener('click', novaImpressora);
    document.getElementById('btn-detectar-impressoras').addEventListener('click', detectarImpressorasSistema);

    // Selects de impressao
    document.getElementById('select-cliente').addEventListener('change', (e) => {
        if (e.target.value) {
            carregarEnderecos(e.target.value);
        } else {
            document.getElementById('select-endereco').innerHTML = '<option value="">-- Selecione um endereco --</option>';
            document.getElementById('select-endereco').disabled = true;
            document.getElementById('endereco-preview').style.display = 'none';
            state.clienteSelecionado = null;
            state.enderecoSelecionado = null;
            atualizarBotoes();
        }
    });

    document.getElementById('select-endereco').addEventListener('change', (e) => {
        exibirEndereco(e.target.value);
    });

    document.getElementById('select-tipo-etiqueta').addEventListener('change', atualizarBotoes);

    // Botoes de impressao
    document.getElementById('btn-preview').addEventListener('click', gerarPreview);
    document.getElementById('btn-download').addEventListener('click', downloadEtiqueta);
    document.getElementById('btn-imprimir').addEventListener('click', imprimir);

    // Busca
    initBuscaClientes();
}

// ============== Inicializacao ==============

document.addEventListener('DOMContentLoaded', async () => {
    initEventListeners();

    // Carregar dados iniciais
    await Promise.all([
        carregarClientes(),
        carregarImpressoras(),
        carregarTiposEtiqueta(),
        carregarRemetente()
    ]);
});
