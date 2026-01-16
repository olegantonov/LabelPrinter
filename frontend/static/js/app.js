/**
 * Sistema de Impressao de Etiquetas v3.0
 * Integracao com Benu ERP
 */

// Estado da aplicacao
const state = {
    impressoras: [],
    tiposEtiqueta: [],
    dadosEtiqueta: null,
    updateAvailable: false
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
            const error = await response.json().catch(() => ({}));
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
            const error = await response.json().catch(() => ({}));
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
    setTimeout(() => toast.classList.remove('show'), 3000);
}

// Tab Navigation
function initTabs() {
    document.querySelectorAll('.tab-btn').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.tab-btn').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
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
    document.querySelectorAll('.modal-close, .modal-cancel').forEach(el => {
        el.addEventListener('click', (e) => e.target.closest('.modal').classList.remove('show'));
    });
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.classList.remove('show');
        });
    });
}

// ============== Benu ERP ==============

async function verificarStatusBenu() {
    const statusEl = document.getElementById('benu-connection-status');
    try {
        const result = await api.get('/api/benu/status');
        if (result.connected) {
            statusEl.textContent = 'Benu: Conectado';
            statusEl.className = 'status-badge enabled';
        } else {
            statusEl.textContent = 'Benu: ' + (result.message || 'Desconectado');
            statusEl.className = 'status-badge disabled';
        }
    } catch (error) {
        statusEl.textContent = 'Benu: Erro';
        statusEl.className = 'status-badge disabled';
    }
}

async function buscarNoBenu() {
    const tipo = document.getElementById('benu-tipo-busca').value;
    const termo = document.getElementById('benu-termo').value;

    if (!termo.trim()) {
        showToast('Digite um termo de busca', 'error');
        return;
    }

    try {
        showToast('Buscando...', 'info');
        let resultados = await api.post('/api/benu/buscar', { tipo, termo });

        const container = document.getElementById('benu-lista-resultados');
        const resultadosDiv = document.getElementById('benu-resultados');

        // Normaliza resultado para array
        if (!resultados) {
            resultados = [];
        } else if (!Array.isArray(resultados)) {
            // Se for objeto, tenta extrair array de propriedades comuns
            if (resultados.data && Array.isArray(resultados.data)) {
                resultados = resultados.data;
            } else if (resultados.lista && Array.isArray(resultados.lista)) {
                resultados = resultados.lista;
            } else if (resultados.items && Array.isArray(resultados.items)) {
                resultados = resultados.items;
            } else if (resultados.content && Array.isArray(resultados.content)) {
                resultados = resultados.content;
            } else {
                // Transforma objeto unico em array
                resultados = [resultados];
            }
        }

        if (resultados.length === 0) {
            container.innerHTML = '<p class="empty-state">Nenhum resultado encontrado</p>';
        } else {
            container.innerHTML = resultados.map((item, index) => `
                <div class="benu-resultado-item" onclick="selecionarResultadoBenu(${index})">
                    <strong>${item.nome || item.cliente || item.razaoSocial || item.nomeCliente || item.nmCliente || 'Sem nome'}</strong>
                    <br>
                    <small>${item.endereco || item.logradouro || item.dsEndereco || ''} ${item.numero || item.nrEndereco || ''}</small>
                    <small>${item.cidade || item.nmCidade || ''} - ${item.uf || item.estado || item.sgEstado || ''}</small>
                </div>
            `).join('');
            // Guarda resultados para uso posterior
            state.resultadosBenu = resultados;
        }

        resultadosDiv.style.display = 'block';
        showToast(`${resultados.length} resultado(s) encontrado(s)`, 'success');
    } catch (error) {
        showToast('Erro ao buscar: ' + error.message, 'error');
        console.error('Erro completo:', error);
    }
}

function selecionarResultadoBenu(index) {
    const item = state.resultadosBenu[index];
    if (!item) return;

    // Preenche o formulario (considera diferentes nomes de campos do Benu)
    document.getElementById('etiq-nome').value =
        item.nome || item.cliente || item.razaoSocial || item.nomeCliente ||
        item.nmCliente || item.nmRazaoSocial || item.dsNome || '';

    document.getElementById('etiq-logradouro').value =
        item.logradouro || item.endereco || item.dsEndereco || item.dsLogradouro || '';

    document.getElementById('etiq-numero').value =
        item.numero || item.nrEndereco || item.nrNumero || '';

    document.getElementById('etiq-complemento').value =
        item.complemento || item.dsComplemento || '';

    document.getElementById('etiq-bairro').value =
        item.bairro || item.dsBairro || item.nmBairro || '';

    document.getElementById('etiq-cidade').value =
        item.cidade || item.nmCidade || item.dsCidade || '';

    document.getElementById('etiq-estado').value =
        item.uf || item.estado || item.sgEstado || item.sgUf || '';

    document.getElementById('etiq-cep').value =
        item.cep || item.nrCep || item.cdCep || '';

    // Mostra o formulario de edicao
    document.getElementById('card-edicao').style.display = 'block';
    document.getElementById('card-edicao').scrollIntoView({ behavior: 'smooth' });

    // Mostra os dados brutos no console para debug
    console.log('Dados do Benu selecionados:', item);

    showToast('Dados carregados - edite se necessario', 'success');
}

// ============== CEP ==============

async function buscarCep() {
    const cep = document.getElementById('etiq-cep').value.replace(/\D/g, '');
    if (cep.length !== 8) {
        showToast('CEP invalido', 'error');
        return;
    }

    try {
        const dados = await api.get(`/api/cep/${cep}`);
        if (dados) {
            if (dados.street) document.getElementById('etiq-logradouro').value = dados.street;
            if (dados.neighborhood) document.getElementById('etiq-bairro').value = dados.neighborhood;
            if (dados.city) document.getElementById('etiq-cidade').value = dados.city;
            if (dados.state) document.getElementById('etiq-estado').value = dados.state;
            showToast('CEP encontrado', 'success');
        }
    } catch (error) {
        showToast('CEP nao encontrado', 'error');
    }
}

// ============== Impressao Direta ==============

function getDadosEtiqueta() {
    return {
        nome: document.getElementById('etiq-nome').value,
        destinatario: document.getElementById('etiq-destinatario').value || null,
        logradouro: document.getElementById('etiq-logradouro').value,
        numero: document.getElementById('etiq-numero').value,
        complemento: document.getElementById('etiq-complemento').value,
        bairro: document.getElementById('etiq-bairro').value,
        cidade: document.getElementById('etiq-cidade').value,
        estado: document.getElementById('etiq-estado').value,
        cep: document.getElementById('etiq-cep').value,
        tipo_etiqueta: document.getElementById('etiq-tipo').value,
        quantidade: parseInt(document.getElementById('etiq-quantidade').value) || 1,
        impressora_id: document.getElementById('etiq-impressora').value || null,
        incluir_codigo_barras: document.getElementById('etiq-codigo-barras').checked,
        incluir_remetente: document.getElementById('etiq-remetente').checked
    };
}

async function gerarPreview() {
    const dados = getDadosEtiqueta();
    try {
        const response = await fetch('/api/preview/direto', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(dados)
        });
        if (!response.ok) throw new Error('Erro ao gerar preview');
        const blob = await response.blob();
        document.getElementById('preview-iframe').src = URL.createObjectURL(blob);
        document.getElementById('preview-container').style.display = 'block';
    } catch (error) {
        showToast('Erro ao gerar preview: ' + error.message, 'error');
    }
}

async function downloadEtiqueta() {
    const dados = getDadosEtiqueta();
    try {
        const response = await fetch('/api/download/direto', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(dados)
        });
        if (!response.ok) throw new Error('Erro ao gerar download');
        const blob = await response.blob();
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = `etiqueta_${dados.nome.replace(/ /g, '_')}.pdf`;
        a.click();
    } catch (error) {
        showToast('Erro ao fazer download: ' + error.message, 'error');
    }
}

async function imprimirEtiqueta(e) {
    e.preventDefault();
    const dados = getDadosEtiqueta();

    if (!dados.nome || !dados.logradouro || !dados.cidade || !dados.cep) {
        showToast('Preencha todos os campos obrigatorios', 'error');
        return;
    }

    try {
        await api.post('/api/imprimir/direto', dados);
        showToast('Etiqueta enviada para impressao!', 'success');
    } catch (error) {
        showToast('Erro ao imprimir: ' + error.message, 'error');
    }
}

function limparFormulario() {
    document.getElementById('form-etiqueta').reset();
    document.getElementById('preview-container').style.display = 'none';
}

// ============== Impressoras ==============

async function carregarImpressoras() {
    try {
        state.impressoras = await api.get('/api/impressoras');
        renderizarImpressoras();
        atualizarSelectImpressoras();
    } catch (error) {
        showToast('Erro ao carregar impressoras', 'error');
    }
}

function renderizarImpressoras() {
    const tbody = document.getElementById('lista-impressoras');
    if (state.impressoras.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="empty-state">Nenhuma impressora cadastrada</td></tr>';
        return;
    }
    tbody.innerHTML = state.impressoras.map(imp => `
        <tr>
            <td>${imp.nome}</td>
            <td>${imp.nome_sistema}</td>
            <td>${imp.tipo}</td>
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
    const select = document.getElementById('etiq-impressora');
    select.innerHTML = '<option value="">-- Usar padrao --</option>';
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
    const imp = state.impressoras.find(i => i.id === id);
    if (!imp) return;
    document.getElementById('modal-impressora-titulo').textContent = 'Editar Impressora';
    document.getElementById('impressora-id').value = imp.id;
    document.getElementById('impressora-nome').value = imp.nome;
    document.getElementById('impressora-nome-sistema').value = imp.nome_sistema;
    document.getElementById('impressora-tipo').value = imp.tipo;
    document.getElementById('impressora-modelo').value = imp.modelo || '';
    document.getElementById('impressora-localizacao').value = imp.localizacao || '';
    openModal('modal-impressora');
}

async function excluirImpressora(id) {
    if (!confirm('Excluir esta impressora?')) return;
    try {
        await api.delete(`/api/impressoras/${id}`);
        showToast('Impressora excluida', 'success');
        carregarImpressoras();
    } catch (error) {
        showToast('Erro ao excluir', 'error');
    }
}

async function salvarImpressora(e) {
    e.preventDefault();
    const id = document.getElementById('impressora-id').value;
    const dados = {
        nome: document.getElementById('impressora-nome').value,
        nome_sistema: document.getElementById('impressora-nome-sistema').value,
        tipo: document.getElementById('impressora-tipo').value,
        modelo: document.getElementById('impressora-modelo').value,
        localizacao: document.getElementById('impressora-localizacao').value
    };
    try {
        if (id) {
            await api.put(`/api/impressoras/${id}`, dados);
        } else {
            await api.post('/api/impressoras', dados);
        }
        showToast('Impressora salva', 'success');
        closeModal('modal-impressora');
        carregarImpressoras();
    } catch (error) {
        showToast('Erro ao salvar', 'error');
    }
}

async function detectarImpressorasSistema() {
    try {
        const impressoras = await api.get('/api/impressoras/sistema');
        const container = document.getElementById('lista-impressoras-sistema');
        if (impressoras.length === 0) {
            container.innerHTML = '<p class="empty-state">Nenhuma impressora detectada</p>';
        } else {
            container.innerHTML = impressoras.map(imp => `
                <div class="impressora-sistema-item">
                    <div>
                        <strong>${imp.name}</strong>
                        <span class="status-badge ${imp.enabled ? 'enabled' : 'disabled'}">${imp.enabled ? 'Ativa' : 'Inativa'}</span>
                    </div>
                    <button class="btn btn-sm btn-primary" onclick="adicionarImpressoraSistema('${imp.name}')">Adicionar</button>
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

// ============== Configuracoes ==============

async function carregarConfiguracoes() {
    try {
        const configs = await api.get('/api/configuracoes-etiqueta');
        const container = document.getElementById('config-etiquetas');
        const tipos = [
            { id: 'thermal_60x30', name: 'Termica 60x30mm' },
            { id: 'thermal_100x80', name: 'Termica 100x80mm' }
        ];
        container.innerHTML = tipos.map(tipo => {
            const config = configs.find(c => c.tipo_etiqueta === tipo.id);
            return `
                <div class="config-item" style="margin-bottom: 10px;">
                    <label>${tipo.name}:</label>
                    <select class="form-control" onchange="salvarConfiguracaoEtiqueta('${tipo.id}', this.value)">
                        <option value="">-- Nenhuma --</option>
                        ${state.impressoras.map(imp => `
                            <option value="${imp.id}" ${config && config.impressora_id === imp.id ? 'selected' : ''}>${imp.nome}</option>
                        `).join('')}
                    </select>
                </div>
            `;
        }).join('');
    } catch (error) {
        console.error(error);
    }
}

async function salvarConfiguracaoEtiqueta(tipo, impressoraId) {
    try {
        await api.put(`/api/configuracoes-etiqueta/${tipo}?impressora_id=${impressoraId || ''}`);
        showToast('Configuracao salva', 'success');
    } catch (error) {
        showToast('Erro ao salvar', 'error');
    }
}

async function carregarSettings() {
    try {
        const settings = await api.get('/api/settings');
        if (settings.benu_api) {
            const token = document.getElementById('benu-token');
            if (token) token.value = settings.benu_api.token || '';
        }
        if (settings.etiquetas) {
            const dpi = document.getElementById('etiqueta-dpi');
            const fonte = document.getElementById('etiqueta-fonte');
            const cepnet = document.getElementById('etiqueta-cepnet');
            const datamatrix = document.getElementById('etiqueta-datamatrix');
            if (dpi) dpi.value = settings.etiquetas.resolucao_dpi || 300;
            if (fonte) fonte.value = settings.etiquetas.tamanho_fonte_min || 10;
            if (cepnet) cepnet.checked = settings.etiquetas.incluir_cepnet !== false;
            if (datamatrix) datamatrix.checked = settings.etiquetas.incluir_datamatrix || false;
        }
    } catch (error) {
        console.error('Erro ao carregar settings:', error);
    }
}

async function salvarTokenBenu() {
    const token = document.getElementById('benu-token').value;
    try {
        await api.post('/api/settings/benu/token', { token });
        showToast('Token salvo', 'success');
        verificarStatusBenu();
    } catch (error) {
        showToast('Erro ao salvar token', 'error');
    }
}

async function testarConexaoBenu() {
    try {
        const result = await api.get('/api/settings/benu/test');
        showToast(result.success ? 'Conexao OK!' : (result.message || 'Falha'), result.success ? 'success' : 'error');
    } catch (error) {
        showToast('Erro ao testar conexao', 'error');
    }
}

async function salvarConfigEtiquetas() {
    const dados = {
        resolucao_dpi: parseInt(document.getElementById('etiqueta-dpi').value) || 300,
        tamanho_fonte_min: parseInt(document.getElementById('etiqueta-fonte').value) || 10,
        incluir_cepnet: document.getElementById('etiqueta-cepnet').checked,
        incluir_datamatrix: document.getElementById('etiqueta-datamatrix').checked
    };
    try {
        await api.post('/api/settings/etiquetas', dados);
        showToast('Configuracoes salvas', 'success');
    } catch (error) {
        showToast('Erro ao salvar', 'error');
    }
}

async function carregarRemetente() {
    try {
        const rem = await api.get('/api/remetente');
        if (rem) {
            document.getElementById('rem-nome').value = rem.nome || '';
            document.getElementById('rem-logradouro').value = rem.logradouro || '';
            document.getElementById('rem-numero').value = rem.numero || '';
            document.getElementById('rem-complemento').value = rem.complemento || '';
            document.getElementById('rem-bairro').value = rem.bairro || '';
            document.getElementById('rem-cidade').value = rem.cidade || '';
            document.getElementById('rem-estado').value = rem.estado || '';
            document.getElementById('rem-cep').value = rem.cep || '';
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
        showToast('Remetente salvo', 'success');
    } catch (error) {
        showToast('Erro ao salvar remetente', 'error');
    }
}

// ============== Atualizacoes ==============

async function carregarVersao() {
    try {
        const version = await api.get('/api/system/version');
        document.getElementById('system-version').textContent = `v${version.commit || '3.0'}`;
        document.getElementById('versao-atual').textContent = version.commit || 'desconhecida';
    } catch (error) {
        console.error(error);
    }
}

async function verificarAtualizacao() {
    try {
        const result = await api.get('/api/system/update/check');
        const statusEl = document.getElementById('atualizacao-status');
        const btnAplicar = document.getElementById('btn-aplicar-atualizacao');

        if (result.available) {
            statusEl.textContent = `Atualizacao disponivel! ${result.commits_behind} commit(s) atras.`;
            statusEl.className = 'status-message success';
            btnAplicar.disabled = false;
            state.updateAvailable = true;
        } else {
            statusEl.textContent = result.message || 'Sistema atualizado';
            statusEl.className = 'status-message info';
            btnAplicar.disabled = true;
        }
        document.getElementById('ultima-verificacao').textContent = new Date().toLocaleString();
    } catch (error) {
        document.getElementById('atualizacao-status').textContent = 'Erro ao verificar: ' + error.message;
    }
}

async function aplicarAtualizacao() {
    if (!confirm('Aplicar atualizacao? O sistema sera reiniciado.')) return;
    try {
        const result = await api.post('/api/system/update/apply');
        showToast(result.message || 'Atualizacao aplicada', 'success');
        if (result.restart_required) {
            showToast('Reinicie o servico para aplicar as mudancas', 'info');
        }
    } catch (error) {
        showToast('Erro ao atualizar: ' + error.message, 'error');
    }
}

// ============== Event Listeners ==============

function initEventListeners() {
    initTabs();
    initModals();

    // Benu
    document.getElementById('btn-buscar-benu').addEventListener('click', buscarNoBenu);
    document.getElementById('benu-termo').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') buscarNoBenu();
    });

    // CEP
    document.getElementById('btn-buscar-cep').addEventListener('click', buscarCep);

    // Etiqueta
    document.getElementById('form-etiqueta').addEventListener('submit', imprimirEtiqueta);
    document.getElementById('btn-preview').addEventListener('click', gerarPreview);
    document.getElementById('btn-download').addEventListener('click', downloadEtiqueta);
    document.getElementById('btn-limpar-form').addEventListener('click', limparFormulario);

    // Impressoras
    document.getElementById('btn-nova-impressora').addEventListener('click', novaImpressora);
    document.getElementById('btn-detectar-impressoras').addEventListener('click', detectarImpressorasSistema);
    document.getElementById('form-impressora').addEventListener('submit', salvarImpressora);

    // Configuracoes
    document.getElementById('btn-salvar-benu-token').addEventListener('click', salvarTokenBenu);
    document.getElementById('btn-testar-benu').addEventListener('click', testarConexaoBenu);
    document.getElementById('btn-salvar-etiqueta-config').addEventListener('click', salvarConfigEtiquetas);
    document.getElementById('form-remetente').addEventListener('submit', salvarRemetente);

    // Atualizacoes
    document.getElementById('btn-verificar-atualizacao').addEventListener('click', verificarAtualizacao);
    document.getElementById('btn-aplicar-atualizacao').addEventListener('click', aplicarAtualizacao);
}

// ============== Inicializacao ==============

document.addEventListener('DOMContentLoaded', async () => {
    initEventListeners();

    // Mostra formulario de edicao vazio para entrada manual
    document.getElementById('card-edicao').style.display = 'block';

    await Promise.all([
        carregarImpressoras(),
        carregarRemetente(),
        carregarSettings(),
        verificarStatusBenu(),
        carregarVersao()
    ]);

    carregarConfiguracoes();
});
