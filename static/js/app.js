/**
 * 小奥会议纪要前端应用
 */

const API_BASE = '';
let currentMeetingId = null;
let recordingTimer = null;
let recordingSeconds = 0;
let wsConnection = null;
let audioContext = null;
let mediaRecorder = null;
let realtimeTranscriptWs = null;
let modelConfigs = [];
let isTranscriptEditMode = false;
let currentTranscripts = []; // 缓存当前会议的原始转录数据
let transcriptEditDirtyMap = new Map(); // 记录哪些片段被修改过 segmentId -> {text, speaker}

// ==================== 初始化 ====================

document.addEventListener('DOMContentLoaded', async () => {
    console.log('[APP] 页面加载完成，开始初始化');
    
    initEventListeners();
    loadDevices();
    loadSettings();
    initWebSocket();
    
    await checkRecordingStatus();
    
    startRecordingStatusPolling();
    
    await loadMeetings();
    
    startMonitoring();
});

async function startMonitoring() {
    try {
        const micDeviceSelect = document.getElementById('mic-device');
        const systemAudioCheckbox = document.getElementById('system-audio');
        const systemDeviceSelect = document.getElementById('system-device');
        
        const micDeviceId = micDeviceSelect && micDeviceSelect.value ? parseInt(micDeviceSelect.value) : 0;
        const enableSystemAudio = systemAudioCheckbox ? systemAudioCheckbox.checked : false;
        const systemDeviceId = enableSystemAudio && systemDeviceSelect && systemDeviceSelect.value 
            ? parseInt(systemDeviceSelect.value) 
            : null;
        
        const response = await fetch(`${API_BASE}/api/recording/monitoring/start/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                mic_device_id: micDeviceId,
                system_device_id: systemDeviceId,
                enable_system_audio: enableSystemAudio
            }),
        });
        const result = await response.json();
        console.log('[Monitoring] 预监听启动:', result, `mic_device_id=${micDeviceId}, enable_system_audio=${enableSystemAudio}`);
    } catch (e) {
        console.error('[Monitoring] 启动预监听失败:', e);
    }
}

function initEventListeners() {
    // 新建会议
    document.getElementById('new-meeting-btn')?.addEventListener('click', createNewMeeting);

    // 录音控制
    document.getElementById('record-btn')?.addEventListener('click', toggleRecording);
    document.getElementById('pause-btn')?.addEventListener('click', togglePause);

    // 系统音频切换
    document.getElementById('enable-system-audio')?.addEventListener('change', (e) => {
        document.getElementById('system-device').disabled = !e.target.checked;
    });

    // 标签页切换
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => switchTab(btn.dataset.tab));
    });

    // 模态框
    document.getElementById('settings-btn')?.addEventListener('click', () => openModal('settings-modal'));
    document.getElementById('import-btn')?.addEventListener('click', () => openModal('import-modal'));
    document.querySelectorAll('.modal-close').forEach(btn => {
        btn.addEventListener('click', closeAllModals);
    });

    // 设置保存
    document.getElementById('save-settings-btn')?.addEventListener('click', saveSettings);

    // AI 模型配置
    document.getElementById('add-model-config-btn')?.addEventListener('click', () => showModelConfigForm());
    document.getElementById('save-model-config-btn')?.addEventListener('click', saveModelConfig);
    document.getElementById('cancel-model-config-btn')?.addEventListener('click', hideModelConfigForm);

    // 搜索
    document.getElementById('search-btn')?.addEventListener('click', searchMeetings);
    document.getElementById('search-input')?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') searchMeetings();
    });

    // 标题编辑
    document.getElementById('meeting-title')?.addEventListener('blur', updateMeetingTitle);

    // 导出和删除
    document.getElementById('export-btn')?.addEventListener('click', exportMeeting);
    document.getElementById('delete-btn')?.addEventListener('click', deleteMeeting);

    // 重新转录
    document.getElementById('retranscribe-btn')?.addEventListener('click', retranscribe);

    // 转录编辑模式
    document.getElementById('edit-mode-btn')?.addEventListener('click', toggleTranscriptEditMode);
    document.getElementById('save-all-transcripts-btn')?.addEventListener('click', saveAllTranscriptChanges);
    document.getElementById('cancel-edit-btn')?.addEventListener('click', cancelTranscriptEdit);

    // 生成摘要
    document.getElementById('generate-summary-btn')?.addEventListener('click', generateSummary);
    document.getElementById('regenerate-summary-btn')?.addEventListener('click', generateSummary);

    // 保存笔记
    document.getElementById('save-notes-btn')?.addEventListener('click', saveNotes);

    // 导入音频
    document.getElementById('file-upload-area')?.addEventListener('click', () => {
        document.getElementById('audio-file-input').click();
    });
    document.getElementById('audio-file-input')?.addEventListener('change', handleFileSelect);
    document.getElementById('start-import-btn')?.addEventListener('click', importAudio);
}

// ==================== 会议列表 ====================

async function loadMeetings() {
    try {
        const response = await fetch(`${API_BASE}/api/meetings/`);
        const meetings = await response.json();
        renderMeetingList(meetings);
    } catch (e) {
        console.error('Failed to load meetings:', e);
    }
}

function renderMeetingList(meetings) {
    const container = document.getElementById('meeting-list');
    if (!container) return;

    container.innerHTML = meetings.map(m => `
        <div class="meeting-item ${m.id === currentMeetingId ? 'active' : ''}" data-id="${m.id}">
            <div class="title">${escapeHtml(m.title)}</div>
            <div class="meta">
                <span>
                    <span class="status-badge status-${m.status}"></span>
                    ${formatStatus(m.status)}
                </span>
                <span>${m.duration_display || '0:00'}</span>
            </div>
        </div>
    `).join('');

    container.querySelectorAll('.meeting-item').forEach(item => {
        item.addEventListener('click', () => selectMeeting(item.dataset.id));
    });
}

async function createNewMeeting() {
    try {
        const response = await fetch(`${API_BASE}/api/meetings/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title: '新会议 ' + new Date().toLocaleString() }),
        });
        const meeting = await response.json();
        
        if (!response.ok) {
            if (response.status === 409 && meeting.error) {
                alert(meeting.error);
            } else {
                alert('创建会议失败: ' + (meeting.error || '未知错误'));
            }
            return;
        }
        
        currentMeetingId = meeting.id;
        await loadMeetings();
        selectMeeting(meeting.id);
    } catch (e) {
        alert('创建会议失败: ' + e.message);
    }
}

async function selectMeeting(meetingId) {
    currentMeetingId = meetingId;

    // 更新选中状态
    document.querySelectorAll('.meeting-item').forEach(item => {
        item.classList.toggle('active', item.dataset.id === meetingId);
    });

    // 加载会议详情
    try {
        const response = await fetch(`${API_BASE}/api/meetings/${meetingId}/`);
        const meeting = await response.json();
        renderMeetingDetail(meeting);
    } catch (e) {
        console.error('Failed to load meeting:', e);
    }
}

function renderMeetingDetail(meeting) {
    document.getElementById('welcome-page')?.classList.add('hidden');
    document.getElementById('meeting-detail')?.classList.remove('hidden');

    const titleInput = document.getElementById('meeting-title');
    if (titleInput) titleInput.value = meeting.title;

    // 渲染音频播放器
    renderAudioPlayer(meeting.audio_file, meeting.audio_duration);

    // 缓存原始转录数据
    currentTranscripts = meeting.transcripts || [];

    // 渲染转录（若失败则显示错误提示）
    if (meeting.transcription_error) {
        const transcriptContent = document.getElementById('transcript-content');
        if (transcriptContent) {
            transcriptContent.innerHTML = `<div class="empty-state" style="color:var(--danger)">转录失败: ${escapeHtml(meeting.transcription_error)}</div>`;
        }
    } else {
        renderTranscripts(meeting.transcripts);
    }

    // 初始化音字联动（绑定音频事件）
    setupAudioSync();

    // 控制编辑模式按钮状态
    const editBtn = document.getElementById('edit-mode-btn');
    if (editBtn) {
        const canEdit = meeting.status !== 'processing' && meeting.status !== 'recording';
        editBtn.disabled = !canEdit;
        editBtn.title = canEdit ? '进入编辑模式' : '录音/转录中不可编辑';
    }
    // 如果正在转录中且当前在编辑模式，强制退出
    if ((meeting.status === 'processing' || meeting.status === 'recording') && isTranscriptEditMode) {
        cancelTranscriptEdit();
    }

    // 如果正在转录中，显示 loading 并轮询
    if (meeting.status === 'processing') {
        showTranscribingState();
        pollMeetingStatus(meeting.id);
    } else {
        hideTranscribingState();
    }

    // 渲染摘要
    if (meeting.summary_data && meeting.summary_data.status === 'failed') {
        const summaryContent = document.getElementById('summary-content');
        if (summaryContent) {
            summaryContent.innerHTML = `<div class="empty-state" style="color:var(--danger)">摘要生成失败: ${escapeHtml(meeting.summary_data.error)}</div>`;
        }
        updateSummaryButtons({ status: 'completed' });
    } else if (meeting.summary) {
        renderSummary(meeting.summary);
        updateSummaryButtons(meeting.summary_data);
    } else {
        const summaryContent = document.getElementById('summary-content');
        if (summaryContent) {
            summaryContent.innerHTML = '<div class="empty-state">点击"生成摘要"按钮生成 AI 摘要</div>';
        }
        updateSummaryButtons(meeting.summary_data);
    }

    // 渲染笔记
    const notesEditor = document.getElementById('notes-editor');
    if (notesEditor) notesEditor.value = meeting.notes || '';

    // 如果正在生成摘要中，显示 loading 并轮询
    if (meeting.summary_data && meeting.summary_data.status === 'processing') {
        showSummaryProcessingState();
        pollSummaryStatus();
    } else {
        hideSummaryProcessingState();
    }
}

function mergeTranscriptSegments(transcripts) {
    if (!transcripts || transcripts.length === 0) return [];

    const merged = [];
    let current = null;

    for (const t of transcripts) {
        const speaker = t.speaker || '发言人';
        if (current && current.speaker === speaker) {
            current.text += ' ' + t.text;
            current.audio_end_time = t.audio_end_time;
            // 合并 words 数组，保持音字联动数据完整
            // 同时给每个 word 标记所属原始段的索引，用于渲染时插入分隔
            if (t.words && t.words.length > 0) {
                const segIdx = current.source_segments.length;
                const markedWords = t.words.map(w => ({
                    ...w,
                    _source_seg_idx: segIdx,
                }));
                current.words = current.words.concat(markedWords);
            }
            current.source_segments.push({
                text: t.text,
                audio_start_time: t.audio_start_time,
                audio_end_time: t.audio_end_time,
                words: t.words || [],
            });
        } else {
            if (current) merged.push(current);
            const initialWords = (t.words || []).map(w => ({
                ...w,
                _source_seg_idx: 0,
            }));
            current = {
                text: t.text,
                speaker: speaker,
                audio_start_time: t.audio_start_time,
                audio_end_time: t.audio_end_time,
                words: initialWords,
                source_segments: [{
                    text: t.text,
                    audio_start_time: t.audio_start_time,
                    audio_end_time: t.audio_end_time,
                    words: t.words || [],
                }],
            };
        }
    }
    if (current) merged.push(current);
    return merged;
}

/**
 * 渲染 segment 中的 words 为可点击的 span，支持音字联动
 * 无 words 数据时回退到 segment 级别联动
 * 若 segment 由多个原始段合并而成，在段间插入视觉分隔符以区分
 */
function renderSegmentWords(segment) {
    const hasWords = segment.words && segment.words.length > 0;
    const hasMultipleSegments = segment.source_segments && segment.source_segments.length > 1;

    if (!hasWords) {
        // 无 words 数据时，如果有多个原始段，为每个子段分别渲染可点击 span
        if (hasMultipleSegments) {
            return segment.source_segments.map((seg, idx) => {
                const start = seg.audio_start_time !== undefined && seg.audio_start_time !== null ? seg.audio_start_time : 0;
                const end = seg.audio_end_time !== undefined && seg.audio_end_time !== null ? seg.audio_end_time : 0;
                const separator = idx > 0 ? '<span class="segment-divider" title="原始段落分隔"></span>' : '';
                return `${separator}<span class="transcript-word" data-segment-level="true" data-start="${start}" data-end="${end}">${escapeHtml(seg.text)}</span>`;
            }).join('');
        }
        // 回退：将整个 segment 文本包装为可点击的 span，使用 segment 级别时间戳
        // 时间戳无效时用 0 兜底，避免 data-start="" 导致高亮逻辑全部跳过
        const start = segment.audio_start_time !== undefined && segment.audio_start_time !== null ? segment.audio_start_time : 0;
        const end = segment.audio_end_time !== undefined && segment.audio_end_time !== null ? segment.audio_end_time : 0;
        return `<span class="transcript-word" data-segment-level="true" data-start="${start}" data-end="${end}">${escapeHtml(segment.text)}</span>`;
    }

    // 有 words 数据时，正常渲染每个 word，并在原始段边界处插入分隔符
    return segment.words.map((w, idx) => {
        const wordText = escapeHtml(w.word || '');
        // word 时间戳无效时用 segment 时间戳兜底，避免 data-start="" 导致高亮跳过
        const segStart = segment.audio_start_time !== undefined && segment.audio_start_time !== null ? segment.audio_start_time : 0;
        const segEnd = segment.audio_end_time !== undefined && segment.audio_end_time !== null ? segment.audio_end_time : 0;
        const start = w.start !== undefined && w.start !== null ? w.start : segStart;
        const end = w.end !== undefined && w.end !== null ? w.end : segEnd;

        // 检测原始段边界，在边界前插入分隔符
        const prevWord = idx > 0 ? segment.words[idx - 1] : null;
        const isBoundary = hasMultipleSegments && prevWord &&
            w._source_seg_idx !== undefined && prevWord._source_seg_idx !== undefined &&
            w._source_seg_idx !== prevWord._source_seg_idx;
        const separator = isBoundary ? '<span class="segment-divider" title="原始段落分隔"></span>' : '';

        return `${separator}<span class="transcript-word" data-word-index="${idx}" data-start="${start}" data-end="${end}">${wordText}</span>`;
    }).join('');
}

function renderTranscripts(transcripts) {
    const container = document.getElementById('transcript-content');
    if (!container) return;

    // 编辑模式下使用编辑器渲染
    if (isTranscriptEditMode) {
        renderTranscriptEditor(transcripts);
        return;
    }

    // 清除旧高亮状态（DOM 即将被替换）
    clearAllHighlights();
    lastHighlightedWord = null;

    if (!transcripts || transcripts.length === 0) {
        container.innerHTML = '<div class="empty-state">暂无转录内容</div>';
        return;
    }

    const merged = mergeTranscriptSegments(transcripts);

    container.innerHTML = merged.map((t, segIdx) => `
        <div class="transcript-segment" data-segment-index="${segIdx}" data-start="${t.audio_start_time || 0}" data-end="${t.audio_end_time || 0}">
            <div class="segment-time">${formatTime(t.audio_start_time)} - ${formatTime(t.audio_end_time)}</div>
            <div class="segment-speaker">${escapeHtml(t.speaker)}</div>
            <div class="segment-text" data-has-words="${t.words && t.words.length > 0 ? 'true' : 'false'}">
                ${renderSegmentWords(t)}
            </div>
        </div>
    `).join('');

    // 绑定字/词点击事件：点击定位到音频对应位置
    const wordSpans = container.querySelectorAll('.transcript-word[data-start]');
    wordSpans.forEach(span => {
        span.addEventListener('click', (e) => {
            const start = parseFloat(e.target.dataset.start);
            if (!isNaN(start)) {
                seekAudio(start);
            }
        });
    });

    console.log('[renderTranscripts] 渲染完成:', {
        segments: merged.length,
        wordSpans: wordSpans.length,
        firstStart: wordSpans.length > 0 ? wordSpans[0].dataset.start : null,
        lastStart: wordSpans.length > 0 ? wordSpans[wordSpans.length - 1].dataset.start : null,
    });
}

function renderAudioPlayer(audioFileUrl, duration) {
    const section = document.getElementById('audio-player-section');
    const audio = document.getElementById('meeting-audio');
    if (!section || !audio) return;

    if (audioFileUrl) {
        // DRF 返回的 FileField 是绝对 URL 或相对路径
        const src = audioFileUrl.startsWith('http') ? audioFileUrl : (audioFileUrl.startsWith('/') ? audioFileUrl : API_BASE + audioFileUrl);
        audio.src = src;
        section.classList.remove('hidden');
    } else {
        audio.src = '';
        section.classList.add('hidden');
    }
}

// ==================== 音字联动 ====================

let lastHighlightedWord = null;
let audioSyncListenersAttached = false;

/**
 * 初始化音频与转录文字的联动事件监听
 */
function setupAudioSync() {
    const audio = document.getElementById('meeting-audio');
    if (!audio) return;

    // 避免重复绑定
    if (audioSyncListenersAttached) {
        audio.removeEventListener('timeupdate', onAudioTimeUpdate);
        audio.removeEventListener('seeked', onAudioSeeked);
        audio.removeEventListener('loadedmetadata', onAudioLoadedMetadata);
    }

    audio.addEventListener('timeupdate', onAudioTimeUpdate);
    audio.addEventListener('seeked', onAudioSeeked);
    audio.addEventListener('loadedmetadata', onAudioLoadedMetadata);
    audioSyncListenersAttached = true;

    console.log('[setupAudioSync] 音频联动已绑定, src:', audio.src, 'duration:', audio.duration);
}

function onAudioLoadedMetadata() {
    const audio = document.getElementById('meeting-audio');
    console.log('[audio] loadedmetadata, duration:', audio?.duration);
}

/**
 * 音频播放进度更新时，高亮当前对应的字/词
 */
function onAudioTimeUpdate() {
    const audio = document.getElementById('meeting-audio');
    if (!audio) return;
    highlightWordAtTime(audio.currentTime);
}

/**
 * 音频拖动(seek)后，自动滚动到对应文字位置
 */
function onAudioSeeked() {
    const audio = document.getElementById('meeting-audio');
    if (!audio) return;
    scrollToWordAtTime(audio.currentTime);
}

/**
 * 根据当前播放时间高亮对应的字/词或 segment
 * 有 words 数据时高亮到字，无 words 数据时高亮到 segment
 */
function highlightWordAtTime(currentTime) {
    try {
        const words = document.querySelectorAll('.transcript-word[data-start]');
        if (words.length === 0) {
            console.log('[highlight] 无 transcript-word 元素');
            return;
        }

        // 收集所有有效 start 时间
        const starts = Array.from(words).map(w => parseFloat(w.dataset.start)).filter(s => !isNaN(s));
        const uniqueStarts = [...new Set(starts)];

        let bestMatch = null;

        // 如果所有时间戳都相同（比如全为 0）且数量大于 1，基于音频进度比例估算
        if (uniqueStarts.length <= 1 && words.length > 1) {
            const audio = document.getElementById('meeting-audio');
            const duration = audio?.duration || 0;
            if (duration > 0) {
                const ratio = Math.min(currentTime / duration, 1);
                const idx = Math.min(Math.floor(ratio * words.length), words.length - 1);
                bestMatch = words[idx];
            } else {
                // 无音频时长信息，默认高亮第一个
                bestMatch = words[0];
            }
        } else {
            // 正常时间戳匹配逻辑
            for (const word of words) {
                const start = parseFloat(word.dataset.start);
                const end = parseFloat(word.dataset.end);
                if (isNaN(start)) continue;

                if (currentTime >= start && (!isNaN(end) && end > start ? currentTime <= end : true)) {
                    bestMatch = word;
                    // 继续向后找，找到最后一个满足条件的（更精确）
                } else if (currentTime >= start) {
                    bestMatch = word;
                }
            }
        }

        if (bestMatch && bestMatch !== lastHighlightedWord) {
            // 清除之前的高亮（包括 word 和 segment）
            clearAllHighlights();
            bestMatch.classList.add('active-word');
            lastHighlightedWord = bestMatch;

            // 始终高亮外层 segment，让用户更容易定位当前段落
            const segment = bestMatch.closest('.transcript-segment');
            if (segment) segment.classList.add('active-segment');

            console.log('[highlight] 已高亮:', {
                currentTime,
                start: bestMatch.dataset.start,
                end: bestMatch.dataset.end,
                text: bestMatch.textContent?.slice(0, 30),
            });
        }
    } catch (err) {
        console.error('[highlight] 高亮出错:', err);
    }
}

/**
 * 清除所有高亮状态
 */
function clearAllHighlights() {
    if (lastHighlightedWord) {
        lastHighlightedWord.classList.remove('active-word');
        lastHighlightedWord = null;
    }
    document.querySelectorAll('.transcript-segment.active-segment').forEach(seg => {
        seg.classList.remove('active-segment');
    });
}

/**
 * 根据当前播放时间滚动到对应的字/词或 segment 位置
 */
function scrollToWordAtTime(currentTime) {
    const words = document.querySelectorAll('.transcript-word[data-start]');
    if (words.length === 0) return;

    // 收集所有有效 start 时间
    const starts = Array.from(words).map(w => parseFloat(w.dataset.start)).filter(s => !isNaN(s));
    const uniqueStarts = [...new Set(starts)];

    let bestMatch = null;

    // 如果所有时间戳都相同（比如全为 0）且数量大于 1，基于音频进度比例估算
    if (uniqueStarts.length <= 1 && words.length > 1) {
        const audio = document.getElementById('meeting-audio');
        const duration = audio?.duration || 0;
        if (duration > 0) {
            const ratio = Math.min(currentTime / duration, 1);
            const idx = Math.min(Math.floor(ratio * words.length), words.length - 1);
            bestMatch = words[idx];
        } else {
            bestMatch = words[0];
        }
    } else {
        for (const word of words) {
            const start = parseFloat(word.dataset.start);
            if (isNaN(start)) continue;
            if (currentTime >= start) {
                bestMatch = word;
            }
        }
    }

    if (bestMatch) {
        bestMatch.scrollIntoView({ behavior: 'smooth', block: 'center' });
        // 同时高亮
        clearAllHighlights();
        bestMatch.classList.add('active-word');
        lastHighlightedWord = bestMatch;

        // 始终高亮外层 segment
        const segment = bestMatch.closest('.transcript-segment');
        if (segment) segment.classList.add('active-segment');
    }
}

/**
 * 点击字/词时跳转到音频对应位置并播放
 */
function seekAudio(time) {
    const audio = document.getElementById('meeting-audio');
    if (!audio || !audio.src) return;
    audio.currentTime = Math.max(0, time);
    const playPromise = audio.play();
    if (playPromise && typeof playPromise.catch === 'function') {
        playPromise.catch(() => {
            // 自动播放策略可能阻止播放，用户可手动点击播放
        });
    }
}

function renderSummary(summary) {
    const container = document.getElementById('summary-content');
    if (!container) return;

    if (!summary || !summary.MeetingNotes) {
        container.innerHTML = '<div class="empty-state">暂无摘要</div>';
        return;
    }

    let html = '';

    if (summary.MeetingName) {
        html += `<h3>${escapeHtml(summary.MeetingName)}</h3>`;
    }

    const sections = summary.MeetingNotes.sections || [];
    sections.forEach(section => {
        html += `<div class="summary-section">`;
        html += `<h4>${escapeHtml(section.title)}</h4>`;

        const blocks = section.blocks || [];
        if (blocks.length > 0) {
            html += '<ul>';
            blocks.forEach(block => {
                html += `<li>${escapeHtml(block.content)}</li>`;
            });
            html += '</ul>';
        }

        html += `</div>`;
    });

    container.innerHTML = html || '<div class="empty-state">摘要内容为空</div>';
}

// ==================== 录音 ====================

async function loadDevices() {
    try {
        const response = await fetch(`${API_BASE}/api/recording/devices/`);
        const data = await response.json();

        const micSelect = document.getElementById('mic-device');
        const systemSelect = document.getElementById('system-device');

        if (micSelect) {
            if (data.microphones && data.microphones.length > 0) {
                micSelect.innerHTML = data.microphones.map(d => `<option value="${d.id}">${escapeHtml(d.name)}</option>`).join('');
                micSelect.value = data.microphones[0].id;
            } else {
                micSelect.innerHTML = '<option value="">选择麦克风</option>';
            }
        }

        if (systemSelect) {
            if (data.system_devices && data.system_devices.length > 0) {
                systemSelect.innerHTML = data.system_devices.map(d => `<option value="${d.id}">${escapeHtml(d.name)}</option>`).join('');
                systemSelect.value = data.system_devices[0].id;
            } else {
                systemSelect.innerHTML = '<option value="">选择系统音频设备</option>';
            }
        }
    } catch (e) {
        console.error('Failed to load devices:', e);
    }
}

async function toggleRecording() {
    const btn = document.getElementById('record-btn');
    const isRecording = btn.classList.contains('recording');

    if (!isRecording) {
        try {
            const statusResponse = await fetch(`${API_BASE}/api/recording/status/`);
            const statusData = await statusResponse.json();
            if (statusData.recording && statusData.meeting_id) {
                alert(`已有会议正在录音中，请先停止当前录音。\n会议ID: ${statusData.meeting_id}`);
                return;
            }
        } catch (e) {
            console.error('检查录音状态失败:', e);
        }

        if (!currentMeetingId) {
            await createNewMeeting();
        } else {
            try {
                const meetingResponse = await fetch(`${API_BASE}/api/meetings/${currentMeetingId}/`);
                const meeting = await meetingResponse.json();
                if (meeting.status === 'completed') {
                    const confirmed = confirm('当前会议已完成，是否创建一个新的会议并开始录音？');
                    if (!confirmed) {
                        return;
                    }
                    await createNewMeeting();
                }
            } catch (e) {
                console.error('检查会议状态失败:', e);
            }
        }

        const micDevice = document.getElementById('mic-device')?.value;
        const systemDevice = document.getElementById('system-device')?.value;
        const enableSystem = document.getElementById('enable-system-audio')?.checked;

        try {
            const response = await fetch(`${API_BASE}/api/recording/start/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    meeting_id: currentMeetingId,
                    mic_device_id: micDevice ? parseInt(micDevice) : null,
                    system_device_id: enableSystem && systemDevice ? parseInt(systemDevice) : null,
                    enable_system_audio: enableSystem,
                }),
            });

            const data = await response.json();
            if (!response.ok) {
                alert('启动录音失败: ' + (data.error || '未知错误'));
                return;
            }
            if (data.status === 'recording') {
                startRecordingUI();
            } else {
                alert('启动录音失败: ' + (data.error || '未知错误'));
            }
        } catch (e) {
            alert('启动录音失败: ' + e.message);
        }
    } else {
        try {
            const response = await fetch(`${API_BASE}/api/recording/stop/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ meeting_id: currentMeetingId }),
            });

            stopRecordingUI();
            await loadMeetings();
            if (currentMeetingId) selectMeeting(currentMeetingId);
        } catch (e) {
            alert('停止录音失败: ' + e.message);
        }
    }
}

async function togglePause() {
    const btn = document.getElementById('pause-btn');
    const isPaused = btn.textContent === '恢复';

    try {
        const endpoint = isPaused ? 'resume' : 'pause';
        await fetch(`${API_BASE}/api/recording/${endpoint}/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ meeting_id: currentMeetingId }),
        });

        btn.textContent = isPaused ? '暂停' : '恢复';
    } catch (e) {
        console.error('Pause/Resume failed:', e);
    }
}

function startRecordingUI() {
    const btn = document.getElementById('record-btn');
    btn.classList.add('recording');
    document.getElementById('record-text').textContent = '停止录音';
    document.getElementById('pause-btn').disabled = false;

    recordingSeconds = 0;
    recordingTimer = setInterval(() => {
        recordingSeconds++;
        document.getElementById('recording-timer').textContent = formatDuration(recordingSeconds);
    }, 1000);
}

function stopRecordingUI() {
    const btn = document.getElementById('record-btn');
    btn.classList.remove('recording');
    document.getElementById('record-text').textContent = '开始录音';
    document.getElementById('pause-btn').disabled = true;
    document.getElementById('pause-btn').textContent = '暂停';

    if (recordingTimer) {
        clearInterval(recordingTimer);
        recordingTimer = null;
    }
    recordingSeconds = 0;
    document.getElementById('recording-timer').textContent = '00:00:00';
}

// ==================== WebSocket ====================

function initWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/recording/level/`;

    console.log('[WS] 尝试连接:', wsUrl);

    try {
        wsConnection = new WebSocket(wsUrl);

        wsConnection.onmessage = (event) => {
            const data = JSON.parse(event.data);
            updateLevelMeters(data);
            handleRecordingStatusFromWS(data);
        };

        wsConnection.onclose = (event) => {
            console.log('[WS] 连接已关闭:', event.code, event.reason);
            setTimeout(initWebSocket, 3000);
        };

        wsConnection.onerror = (event) => {
            console.error('[WS] 连接错误:', event);
        };

        wsConnection.onopen = () => {
            console.log('[WS] 连接成功');
            if (wsConnection) {
                wsConnection.send(JSON.stringify({ action: 'get_status' }));
            }
        };
    } catch (e) {
        console.error('[WS] 创建连接失败:', e);
    }
}

function handleRecordingStatusFromWS(data) {
    console.log('[WS] 收到状态数据:', data);
    
    if (data.recording !== undefined) {
        const isRecording = data.recording;
        const btn = document.getElementById('record-btn');
        const isUIRecording = btn?.classList.contains('recording');
        
        console.log('[WS] 状态对比: isRecording=' + isRecording + ', isUIRecording=' + isUIRecording);

        if (isRecording && data.meeting_id) {
            if (!isUIRecording) {
                console.log('[WS] 检测到录音已开始，更新UI');
                currentMeetingId = data.meeting_id;
                startRecordingUI();
                loadMeetings().then(() => {
                    selectMeeting(data.meeting_id);
                });
            }
            
            if (data.duration !== undefined) {
                recordingSeconds = Math.floor(data.duration);
                document.getElementById('recording-timer').textContent = formatDuration(recordingSeconds);
            }
        } else if (!isRecording && isUIRecording) {
            console.log('[WS] 检测到录音已停止，更新UI');
            stopRecordingUI();
            loadMeetings();
        } else if (!isRecording && !isUIRecording) {
            console.log('[WS] 状态一致，无需更新');
        } else if (isRecording && !data.meeting_id) {
            console.log('[WS] 异常: isRecording=true但meeting_id为空');
        }
    }
}

// ==================== 录音状态同步 ====================

let recordingStatusPollInterval = null;

function startRecordingStatusPolling() {
    if (recordingStatusPollInterval) {
        clearInterval(recordingStatusPollInterval);
    }
    
    recordingStatusPollInterval = setInterval(async () => {
        await checkRecordingStatus();
    }, 3000);
}

async function checkRecordingStatus() {
    try {
        const response = await fetch(`${API_BASE}/api/recording/status/`);
        const data = await response.json();
        
        console.log('[Poll] 轮询录音状态:', data);
        
        if (data.recording !== undefined) {
            const isRecording = data.recording;
            const btn = document.getElementById('record-btn');
            const isUIRecording = btn?.classList.contains('recording');
            
            console.log('[Poll] 状态对比: isRecording=' + isRecording + ', isUIRecording=' + isUIRecording);
            console.log('[Poll] currentMeetingId=' + currentMeetingId);

            if (isRecording && data.meeting_id) {
                if (!isUIRecording) {
                    console.log('[Poll] 检测到录音已开始，更新UI');
                    currentMeetingId = data.meeting_id;
                    startRecordingUI();
                    await loadMeetings();
                    selectMeeting(data.meeting_id);
                } else if (currentMeetingId !== data.meeting_id) {
                    console.log('[Poll] 检测到会议切换，更新UI');
                    currentMeetingId = data.meeting_id;
                    await loadMeetings();
                    selectMeeting(data.meeting_id);
                }
                
                if (data.duration !== undefined) {
                    recordingSeconds = Math.floor(data.duration);
                    document.getElementById('recording-timer').textContent = formatDuration(recordingSeconds);
                }
            } else if (!isRecording && isUIRecording) {
                console.log('[Poll] 检测到录音已停止，更新UI');
                stopRecordingUI();
                console.log('[Poll] 调用loadMeetings()...');
                await loadMeetings();
                console.log('[Poll] loadMeetings()完成');
                if (currentMeetingId) {
                    console.log('[Poll] 调用selectMeeting(' + currentMeetingId + ')');
                    selectMeeting(currentMeetingId);
                }
            } else if (!isRecording && !isUIRecording) {
                console.log('[Poll] 状态一致，无需更新');
                
                if (data.meeting_id && currentMeetingId !== data.meeting_id) {
                    console.log('[Poll] 检测到有活跃会议但未录音，同步会议列表');
                    currentMeetingId = data.meeting_id;
                    await loadMeetings();
                    selectMeeting(data.meeting_id);
                }
                if (currentMeetingId) {
                    console.log('[Poll] 但currentMeetingId不为空，检查会议列表是否需要更新');
                    await loadMeetings();
                }
            } else if (isRecording && !data.meeting_id) {
                console.log('[Poll] 异常: isRecording=true但meeting_id为空');
            }
        }
    } catch (e) {
        console.error('[Poll] 检查录音状态失败:', e);
    }
}

function updateLevelMeters(data) {
    const micLevel = document.getElementById('mic-level');
    const systemLevel = document.getElementById('system-level');
    const micValue = document.getElementById('mic-level-value');
    const systemValue = document.getElementById('system-level-value');

    const micLevelVal = typeof data.mic_level === 'number' ? data.mic_level : 0;
    const systemLevelVal = typeof data.system_level === 'number' ? data.system_level : 0;

    if (micLevel) micLevel.style.width = `${Math.min(micLevelVal * 100, 100)}%`;
    if (systemLevel) systemLevel.style.width = `${Math.min(systemLevelVal * 100, 100)}%`;

    if (micValue) micValue.textContent = micLevelVal > 0 ? `${(micLevelVal * 100).toFixed(1)}%` : '-∞ dB';
    if (systemValue) systemValue.textContent = systemLevelVal > 0 ? `${(systemLevelVal * 100).toFixed(1)}%` : '-∞ dB';

    if (data.agc) {
        let agcText = '';
        if (data.agc.enabled) {
            agcText = `AGC: 麦克风声增益 ${data.agc.mic_gain}x`;
            if (data.agc.system_gain > 1.0) {
                agcText += ` / 系统音增益 ${data.agc.system_gain}x`;
            }
        }
        const timerEl = document.getElementById('recording-timer');
        if (timerEl && agcText) {
            timerEl.title = agcText;
        }
    }
}

// ==================== 转录 ====================

async function retranscribe() {
    if (!currentMeetingId) return;

    const language = document.getElementById('transcript-language')?.value || 'auto';

    try {
        const response = await fetch(`${API_BASE}/api/transcription/retranscribe/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                meeting_id: currentMeetingId,
                language: language,
            }),
        });

        const data = await response.json();
        showTranscribingState();
        pollMeetingStatus(currentMeetingId);
        alert('重新转录已开始，请稍候...');
    } catch (e) {
        alert('重新转录失败: ' + e.message);
    }
}

async function importAudio() {
    const fileInput = document.getElementById('audio-file-input');
    const language = document.getElementById('import-language')?.value || 'auto';

    if (!fileInput.files || fileInput.files.length === 0) {
        alert('请选择音频文件');
        return;
    }

    const file = fileInput.files[0];
    const fileName = file.name.toLowerCase();
    if (fileName.endsWith('.m4a')) {
        alert('不支持导入 m4a 格式的音频文件，请选择其他格式');
        return;
    }

    const formData = new FormData();
    formData.append('audio', file);
    formData.append('language', language);
    formData.append('title', file.name);

    try {
        const response = await fetch(`${API_BASE}/api/transcription/upload/`, {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            let errorMsg = `导入失败: HTTP ${response.status}`;
            try {
                const errorData = await response.json();
                if (errorData.error) {
                    errorMsg = '导入失败: ' + errorData.error;
                }
            } catch (e) {
                const text = await response.text();
                const match = text.match(/<title>([^<]+)<\/title>/i);
                if (match) {
                    errorMsg = '导入失败: ' + match[1].replace(/\s+/g, ' ').trim();
                }
            }
            alert(errorMsg);
            return;
        }

        const data = await response.json();
        closeAllModals();
        await loadMeetings();
        selectMeeting(data.meeting_id);
    } catch (e) {
        alert('导入失败: ' + e.message);
    }
}

function handleFileSelect(e) {
    const file = e.target.files[0];
    if (file) {
        document.querySelector('#file-upload-area p').textContent = `已选择: ${file.name}`;
    }
}

// ==================== 摘要 ====================

async function generateSummary() {
    if (!currentMeetingId) return;

    const language = document.getElementById('summary-language')?.value || 'zh';
    const defaultConfig = modelConfigs.find(c => c.is_default);
    const provider = defaultConfig?.provider || document.getElementById('summary-provider')?.value || 'ollama';
    const modelName = defaultConfig?.model_name || 'llama3';

    try {
        const response = await fetch(`${API_BASE}/api/summary/generate/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                meeting_id: currentMeetingId,
                provider: provider,
                model_name: modelName,
                language: language,
            }),
        });

        const data = await response.json();
        if (data.status === 'processing') {
            showSummaryProcessingState();
            pollSummaryStatus();
        }
    } catch (e) {
        alert('生成摘要失败: ' + e.message);
    }
}

function pollSummaryStatus() {
    if (!currentMeetingId) return;

    // 避免重复轮询
    if (summaryPollInterval) {
        clearInterval(summaryPollInterval);
        summaryPollInterval = null;
    }

    summaryPollInterval = setInterval(async () => {
        try {
            const response = await fetch(`${API_BASE}/api/summary/status/${currentMeetingId}/`);
            const data = await response.json();

            if (data.status === 'completed') {
                clearInterval(summaryPollInterval);
                summaryPollInterval = null;
                hideSummaryProcessingState();
                renderSummary(data.data);
                updateSummaryButtons({ status: 'completed' });
            } else if (data.status === 'failed') {
                clearInterval(summaryPollInterval);
                summaryPollInterval = null;
                hideSummaryProcessingState();
                const summaryContent = document.getElementById('summary-content');
                if (summaryContent) {
                    summaryContent.innerHTML = `<div class="empty-state" style="color:var(--danger)">摘要生成失败: ${escapeHtml(data.error)}</div>`;
                }
                updateSummaryButtons({ status: 'completed' });
            }
        } catch (e) {
            console.error('Poll error:', e);
        }
    }, 2000);
}

function updateSummaryButtons(summaryData) {
    const generateBtn = document.getElementById('generate-summary-btn');
    const regenerateBtn = document.getElementById('regenerate-summary-btn');

    if (summaryData && summaryData.status === 'completed') {
        generateBtn?.classList.add('hidden');
        regenerateBtn?.classList.remove('hidden');
    } else {
        generateBtn?.classList.remove('hidden');
        regenerateBtn?.classList.add('hidden');
    }
}

// ==================== 笔记 ====================

async function saveNotes() {
    if (!currentMeetingId) return;

    const notes = document.getElementById('notes-editor')?.value || '';

    try {
        await fetch(`${API_BASE}/api/meetings/${currentMeetingId}/`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ notes: notes }),
        });

        alert('笔记已保存');
    } catch (e) {
        alert('保存笔记失败: ' + e.message);
    }
}

// ==================== 搜索 ====================

async function searchMeetings() {
    const query = document.getElementById('search-input')?.value?.trim();
    if (!query) {
        loadMeetings();
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/meetings/search/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query }),
        });
        const results = await response.json();
        renderSearchResults(results);
    } catch (e) {
        console.error('Search failed:', e);
    }
}

function renderSearchResults(results) {
    const container = document.getElementById('meeting-list');
    if (!container) return;

    if (results.length === 0) {
        container.innerHTML = '<div class="empty-state" style="padding:20px;color:rgba(255,255,255,0.6)">未找到匹配结果</div>';
        return;
    }

    container.innerHTML = results.map(r => `
        <div class="meeting-item" data-id="${r.id}">
            <div class="title">${escapeHtml(r.title)}</div>
            <div class="meta" style="font-size:0.75rem;color:rgba(255,255,255,0.6);margin-top:4px">
                ${escapeHtml(r.match_context)}
            </div>
        </div>
    `).join('');

    container.querySelectorAll('.meeting-item').forEach(item => {
        item.addEventListener('click', () => selectMeeting(item.dataset.id));
    });
}

// ==================== 其他功能 ====================

async function updateMeetingTitle() {
    if (!currentMeetingId) return;

    const title = document.getElementById('meeting-title')?.value;
    if (!title) return;

    try {
        await fetch(`${API_BASE}/api/meetings/${currentMeetingId}/`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title }),
        });
        loadMeetings();
    } catch (e) {
        console.error('Update title failed:', e);
    }
}

async function exportMeeting() {
    if (!currentMeetingId) return;

    const format = prompt('选择导出格式 (txt/md/json):', 'md');
    if (!format) return;

    try {
        const response = await fetch(`${API_BASE}/api/meetings/${currentMeetingId}/export/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ format }),
        });

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `meeting_${currentMeetingId}.${format}`;
        a.click();
        window.URL.revokeObjectURL(url);
    } catch (e) {
        alert('导出失败: ' + e.message);
    }
}

async function deleteMeeting() {
    if (!currentMeetingId) return;

    if (!confirm('确定要删除这个会议吗？此操作不可撤销。')) return;

    try {
        await fetch(`${API_BASE}/api/meetings/${currentMeetingId}/`, {
            method: 'DELETE',
        });

        currentMeetingId = null;
        document.getElementById('meeting-detail')?.classList.add('hidden');
        document.getElementById('welcome-page')?.classList.remove('hidden');
        loadMeetings();
    } catch (e) {
        alert('删除失败: ' + e.message);
    }
}

function switchTab(tabName) {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabName);
    });
    document.querySelectorAll('.tab-panel').forEach(panel => {
        panel.classList.toggle('active', panel.id === `${tabName}-panel`);
    });
}

function openModal(modalId) {
    document.getElementById(modalId)?.classList.remove('hidden');
}

function closeAllModals() {
    document.querySelectorAll('.modal').forEach(m => m.classList.add('hidden'));
}

async function loadSettings() {
    try {
        const response = await fetch(`${API_BASE}/api/system/settings/`);
        const settings = await response.json();

        document.getElementById('setting-minimize-tray').checked = settings.minimize_to_tray;
        document.getElementById('setting-enable-notifications').checked = settings.enable_notifications;

        const oddasrInput = document.getElementById('oddasr-host');
        if (oddasrInput && settings.oddasr_host) {
            oddasrInput.value = settings.oddasr_host;
        }

        await loadModelConfigs();
    } catch (e) {
        console.error('Failed to load settings:', e);
    }
}

// ==================== AI 模型配置 ====================

async function loadModelConfigs() {
    try {
        const response = await fetch(`${API_BASE}/api/summary/model-config/`);
        modelConfigs = await response.json();
        renderModelConfigs();

        // 自动将摘要面板的 provider 下拉框同步为默认配置
        const defaultConfig = modelConfigs.find(c => c.is_default);
        const providerSelect = document.getElementById('summary-provider');
        if (defaultConfig && providerSelect) {
            // 若默认配置的 provider 在下拉选项中存在则选中，否则保持当前值
            const optionExists = Array.from(providerSelect.options).some(o => o.value === defaultConfig.provider);
            if (optionExists) {
                providerSelect.value = defaultConfig.provider;
            }
        }
    } catch (e) {
        console.error('Failed to load model configs:', e);
    }
}

function renderModelConfigs() {
    const container = document.getElementById('model-config-list');
    if (!container) return;

    if (modelConfigs.length === 0) {
        container.innerHTML = '<div class="empty-state" style="padding:8px;color:#999;font-size:0.85rem">暂无模型配置，请添加一个</div>';
        return;
    }

    container.innerHTML = modelConfigs.map(c => `
        <div class="model-config-item" style="display:flex;justify-content:space-between;align-items:center;padding:8px 10px;margin-bottom:6px;border:1px solid #e0e0e0;border-radius:6px;background:#fff">
            <div style="flex:1;min-width:0">
                <div style="font-weight:500;font-size:0.9rem">${escapeHtml(c.provider)} / ${escapeHtml(c.model_name)} ${c.is_default ? '<span style="color:#1976d2;font-size:0.75rem">[默认]</span>' : ''}</div>
                <div style="font-size:0.8rem;color:#888;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${escapeHtml(c.base_url || '')}</div>
            </div>
            <div style="display:flex;gap:4px;margin-left:8px">
                <button class="btn-icon edit-config-btn" data-id="${c.id}" title="编辑" style="background:none;border:none;cursor:pointer;font-size:1rem">&#9999;&#65039;</button>
                <button class="btn-icon delete-config-btn" data-id="${c.id}" title="删除" style="background:none;border:none;cursor:pointer;font-size:1rem">&#128465;&#65039;</button>
            </div>
        </div>
    `).join('');

    container.querySelectorAll('.edit-config-btn').forEach(btn => {
        btn.addEventListener('click', () => editModelConfig(btn.dataset.id));
    });
    container.querySelectorAll('.delete-config-btn').forEach(btn => {
        btn.addEventListener('click', () => deleteModelConfig(btn.dataset.id));
    });
}

function showModelConfigForm(config = null) {
    const form = document.getElementById('model-config-form');
    if (!form) {
        console.error('model-config-form element not found');
        return;
    }

    const idInput = document.getElementById('model-config-id');
    const provider = document.getElementById('model-config-provider');
    const nameInput = document.getElementById('model-config-name');
    const apiKey = document.getElementById('model-config-api-key');
    const baseUrl = document.getElementById('model-config-base-url');
    const isDefault = document.getElementById('model-config-is-default');

    if (!idInput || !provider || !nameInput || !apiKey || !baseUrl || !isDefault) {
        console.error('Some model config form elements are missing');
        return;
    }

    if (config) {
        idInput.value = config.id;
        provider.value = config.provider;
        nameInput.value = config.model_name;
        apiKey.value = config.api_key || '';
        baseUrl.value = config.base_url || '';
        isDefault.checked = config.is_default;
    } else {
        idInput.value = '';
        provider.value = 'ollama';
        nameInput.value = '';
        apiKey.value = '';
        baseUrl.value = '';
        isDefault.checked = modelConfigs.length === 0;
    }

    form.classList.remove('hidden');
}

function hideModelConfigForm() {
    document.getElementById('model-config-form')?.classList.add('hidden');
}

function editModelConfig(configId) {
    const config = modelConfigs.find(c => c.id === configId);
    if (config) showModelConfigForm(config);
}

async function deleteModelConfig(configId) {
    if (!confirm('确定要删除这个模型配置吗？')) return;

    try {
        await fetch(`${API_BASE}/api/summary/model-config/`, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: configId }),
        });
        await loadModelConfigs();
    } catch (e) {
        alert('删除失败: ' + e.message);
    }
}

async function saveModelConfig() {
    const idInput = document.getElementById('model-config-id');
    const providerInput = document.getElementById('model-config-provider');
    const nameInput = document.getElementById('model-config-name');
    const apiKeyInput = document.getElementById('model-config-api-key');
    const baseUrlInput = document.getElementById('model-config-base-url');
    const isDefaultInput = document.getElementById('model-config-is-default');

    if (!idInput || !providerInput || !nameInput || !apiKeyInput || !baseUrlInput || !isDefaultInput) {
        console.error('Model config form elements not found');
        alert('表单元素加载失败，请刷新页面重试');
        return;
    }

    const id = idInput.value;
    const provider = providerInput.value;
    const modelName = nameInput.value.trim();
    const apiKey = apiKeyInput.value;
    const baseUrl = baseUrlInput.value.trim();
    const isDefault = isDefaultInput.checked;

    if (!provider || !modelName) {
        alert('请填写提供商和模型名称');
        return;
    }

    const payload = {
        provider,
        model_name: modelName,
        api_key: apiKey,
        base_url: baseUrl,
        is_default: isDefault,
    };

    try {
        if (id) {
            payload.id = id;
            await fetch(`${API_BASE}/api/summary/model-config/`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
        } else {
            await fetch(`${API_BASE}/api/summary/model-config/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
        }
        hideModelConfigForm();
        await loadModelConfigs();
    } catch (e) {
        alert('保存配置失败: ' + e.message);
    }
}

async function saveSettings() {
    try {
        await fetch(`${API_BASE}/api/system/settings/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                minimize_to_tray: document.getElementById('setting-minimize-tray').checked,
                enable_notifications: document.getElementById('setting-enable-notifications').checked,
                oddasr_host: document.getElementById('oddasr-host')?.value || '127.0.0.1:9002',
            }),
        });
        closeAllModals();
        alert('设置已保存');
    } catch (e) {
        alert('保存设置失败: ' + e.message);
    }
}

// ==================== 工具函数 ====================

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatStatus(status) {
    const map = {
        'idle': '待开始',
        'recording': '录音中',
        'paused': '已暂停',
        'completed': '已完成',
        'processing': '处理中',
    };
    return map[status] || status;
}

function formatTime(seconds) {
    if (seconds === null || seconds === undefined) return '0:00';
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
}

function formatDuration(totalSeconds) {
    const h = Math.floor(totalSeconds / 3600);
    const m = Math.floor((totalSeconds % 3600) / 60);
    const s = totalSeconds % 60;
    return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
}

// ==================== 转录中状态管理 ====================

let transcribePollInterval = null;
let summaryPollInterval = null;

function showSummaryProcessingState() {
    const indicator = document.getElementById('summary-processing-indicator');
    const content = document.getElementById('summary-content');
    if (indicator) indicator.classList.remove('hidden');
    if (content) content.classList.add('hidden');

    // 禁用生成按钮防止重复点击
    const generateBtn = document.getElementById('generate-summary-btn');
    const regenerateBtn = document.getElementById('regenerate-summary-btn');
    if (generateBtn) generateBtn.disabled = true;
    if (regenerateBtn) regenerateBtn.disabled = true;
}

function hideSummaryProcessingState() {
    const indicator = document.getElementById('summary-processing-indicator');
    const content = document.getElementById('summary-content');
    if (indicator) indicator.classList.add('hidden');
    if (content) content.classList.remove('hidden');

    // 恢复按钮状态
    const generateBtn = document.getElementById('generate-summary-btn');
    const regenerateBtn = document.getElementById('regenerate-summary-btn');
    if (generateBtn) generateBtn.disabled = false;
    if (regenerateBtn) regenerateBtn.disabled = false;
}

function showTranscribingState() {
    const indicator = document.getElementById('transcribing-indicator');
    const content = document.getElementById('transcript-content');
    if (indicator) indicator.classList.remove('hidden');
    if (content) content.classList.add('hidden');
}

function hideTranscribingState() {
    const indicator = document.getElementById('transcribing-indicator');
    const content = document.getElementById('transcript-content');
    if (indicator) indicator.classList.add('hidden');
    if (content) content.classList.remove('hidden');
}

function pollMeetingStatus(meetingId) {
    if (transcribePollInterval) {
        clearInterval(transcribePollInterval);
        transcribePollInterval = null;
    }

    transcribePollInterval = setInterval(async () => {
        try {
            const response = await fetch(`${API_BASE}/api/meetings/${meetingId}/`);
            const meeting = await response.json();

            if (meeting.status !== 'processing') {
                clearInterval(transcribePollInterval);
                transcribePollInterval = null;
                hideTranscribingState();
                renderMeetingDetail(meeting);
            }
        } catch (e) {
            console.error('Poll meeting status error:', e);
        }
    }, 3000);
}

// ==================== 转录编辑功能 ====================

function toggleTranscriptEditMode() {
    if (!currentMeetingId) return;

    // 转录中时不允许进入编辑模式
    const editBtn = document.getElementById('edit-mode-btn');
    if (editBtn && editBtn.disabled) {
        alert('当前正在转录中，请等待转录完成后再编辑');
        return;
    }

    isTranscriptEditMode = !isTranscriptEditMode;

    if (isTranscriptEditMode) {
        // 进入编辑模式
        transcriptEditDirtyMap.clear();
        updateTranscriptEditToolbar(true);

        // 暂停音频，避免编辑时联动干扰
        const audio = document.getElementById('meeting-audio');
        if (audio) audio.pause();
        clearAllHighlights();

        renderTranscripts(currentTranscripts);
    } else {
        // 退出编辑模式（正常保存后退出或通过取消按钮）
        cancelTranscriptEdit();
    }
}

function updateTranscriptEditToolbar(inEditMode) {
    const editBtn = document.getElementById('edit-mode-btn');
    const saveAllBtn = document.getElementById('save-all-transcripts-btn');
    const cancelBtn = document.getElementById('cancel-edit-btn');
    const retranscribeBtn = document.getElementById('retranscribe-btn');
    const langSelect = document.getElementById('transcript-language');

    if (inEditMode) {
        editBtn?.classList.add('hidden');
        saveAllBtn?.classList.remove('hidden');
        cancelBtn?.classList.remove('hidden');
        retranscribeBtn?.classList.add('hidden');
        if (langSelect) langSelect.style.display = 'none';
    } else {
        editBtn?.classList.remove('hidden');
        saveAllBtn?.classList.add('hidden');
        cancelBtn?.classList.add('hidden');
        retranscribeBtn?.classList.remove('hidden');
        if (langSelect) langSelect.style.display = '';
    }
}

function renderTranscriptEditor(transcripts) {
    const container = document.getElementById('transcript-content');
    if (!container) return;

    clearAllHighlights();
    lastHighlightedWord = null;

    if (!transcripts || transcripts.length === 0) {
        container.innerHTML = '<div class="empty-state">暂无转录内容</div>';
        return;
    }

    // 按原始片段逐条渲染（不合并）
    container.innerHTML = transcripts.map((t, idx) => {
        const segId = t.id;
        const speaker = escapeHtml(t.speaker || '发言人');
        const text = escapeHtml(t.text || '');
        const startTime = formatTime(t.audio_start_time);
        const endTime = formatTime(t.audio_end_time);
        const isFinal = t.is_final !== false;
        const finalWarning = isFinal ? '' : '<span class="edit-warning" title="该片段为实时转录，可能被后续更新覆盖">⚠️</span>';

        return `
            <div class="transcript-edit-card" data-segment-id="${segId}" data-index="${idx}">
                <div class="edit-card-header">
                    <span class="edit-time">${startTime} - ${endTime}</span>
                    <input type="text" class="edit-speaker-input" value="${speaker}" placeholder="发言人" data-field="speaker">
                    ${finalWarning}
                    <button class="btn-save-segment" data-segment-id="${segId}">保存</button>
                </div>
                <div class="edit-textarea" contenteditable="true" data-field="text" data-original="${text}">${text}</div>
            </div>
        `;
    }).join('');

    // 绑定输入事件：标记为已修改
    container.querySelectorAll('.edit-textarea').forEach(textarea => {
        textarea.addEventListener('input', onTranscriptEditInput);
    });
    container.querySelectorAll('.edit-speaker-input').forEach(input => {
        input.addEventListener('input', onTranscriptEditInput);
    });

    // 绑定保存按钮
    container.querySelectorAll('.btn-save-segment').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const segmentId = e.target.dataset.segmentId;
            saveSingleSegmentFromUI(segmentId);
        });
    });
}

function onTranscriptEditInput(e) {
    const card = e.target.closest('.transcript-edit-card');
    if (!card) return;

    const segmentId = card.dataset.segmentId;
    const textarea = card.querySelector('.edit-textarea[data-field="text"]');
    const speakerInput = card.querySelector('.edit-speaker-input[data-field="speaker"]');

    const text = textarea ? textarea.innerText.trim().replace(/\n+/g, ' ') : '';
    const speaker = speakerInput ? speakerInput.value.trim() : '';

    // 与原始值比较，确定是否有修改
    const originalText = textarea ? textarea.dataset.original : '';
    const originalSpeaker = speakerInput ? speakerInput.dataset.originalValue || speakerInput.defaultValue : '';

    const hasChanges = text !== originalText || speaker !== originalSpeaker;

    const saveBtn = card.querySelector('.btn-save-segment');
    if (saveBtn) {
        if (hasChanges) {
            saveBtn.classList.add('has-changes');
            saveBtn.textContent = '保存 *';
        } else {
            saveBtn.classList.remove('has-changes');
            saveBtn.textContent = '保存';
        }
    }

    if (hasChanges) {
        transcriptEditDirtyMap.set(segmentId, { text, speaker });
    } else {
        transcriptEditDirtyMap.delete(segmentId);
    }
}

async function saveSingleSegmentFromUI(segmentId) {
    const card = document.querySelector(`.transcript-edit-card[data-segment-id="${segmentId}"]`);
    if (!card) return;

    const textarea = card.querySelector('.edit-textarea[data-field="text"]');
    const speakerInput = card.querySelector('.edit-speaker-input[data-field="speaker"]');

    const text = textarea ? textarea.innerText.trim().replace(/\n+/g, ' ') : '';
    const speaker = speakerInput ? speakerInput.value.trim() : '';

    if (!text) {
        alert('文本内容不能为空');
        return;
    }

    const saveBtn = card.querySelector('.btn-save-segment');
    if (saveBtn) {
        saveBtn.disabled = true;
        saveBtn.textContent = '保存中...';
    }

    try {
        await saveTranscriptSegment(segmentId, text, speaker);

        // 更新原始值标记
        if (textarea) textarea.dataset.original = text;
        if (speakerInput) speakerInput.dataset.originalValue = speaker;

        transcriptEditDirtyMap.delete(segmentId);

        if (saveBtn) {
            saveBtn.disabled = false;
            saveBtn.textContent = '已保存';
            saveBtn.classList.remove('has-changes');
            setTimeout(() => {
                if (saveBtn.textContent === '已保存') {
                    saveBtn.textContent = '保存';
                }
            }, 1500);
        }
    } catch (e) {
        alert('保存失败: ' + e.message);
        if (saveBtn) {
            saveBtn.disabled = false;
            saveBtn.textContent = '保存 *';
        }
    }
}

async function saveTranscriptSegment(segmentId, text, speaker) {
    const payload = {};
    if (text !== undefined) payload.text = text;
    if (speaker !== undefined) payload.speaker = speaker;

    const response = await fetch(`${API_BASE}/api/meetings/transcript-segments/${segmentId}/`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
    });

    if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.error || `HTTP ${response.status}`);
    }

    const updated = await response.json();

    // 同步更新本地缓存
    const idx = currentTranscripts.findIndex(t => t.id === segmentId);
    if (idx >= 0) {
        currentTranscripts[idx] = { ...currentTranscripts[idx], ...updated };
    }

    return updated;
}

async function saveAllTranscriptChanges() {
    if (transcriptEditDirtyMap.size === 0) {
        // 没有修改，直接退出编辑模式
        isTranscriptEditMode = false;
        updateTranscriptEditToolbar(false);
        renderTranscripts(currentTranscripts);
        return;
    }

    const saveAllBtn = document.getElementById('save-all-transcripts-btn');
    if (saveAllBtn) {
        saveAllBtn.disabled = true;
        saveAllBtn.textContent = '保存中...';
    }

    try {
        const promises = [];
        for (const [segmentId, data] of transcriptEditDirtyMap) {
            promises.push(saveTranscriptSegment(segmentId, data.text, data.speaker));
        }
        await Promise.all(promises);

        transcriptEditDirtyMap.clear();
        isTranscriptEditMode = false;
        updateTranscriptEditToolbar(false);
        renderTranscripts(currentTranscripts);

        // 更新会议列表中的显示（标题等可能未变，但转录内容已更新）
        if (currentMeetingId) {
            const response = await fetch(`${API_BASE}/api/meetings/${currentMeetingId}/`);
            const meeting = await response.json();
            currentTranscripts = meeting.transcripts || [];
            // 使用服务器最新数据重新渲染查看模式
            renderTranscripts(currentTranscripts);
        }
    } catch (e) {
        alert('批量保存失败: ' + e.message);
    } finally {
        if (saveAllBtn) {
            saveAllBtn.disabled = false;
            saveAllBtn.textContent = '保存全部';
        }
    }
}

function cancelTranscriptEdit() {
    if (transcriptEditDirtyMap.size > 0) {
        if (!confirm('有未保存的修改，确定要放弃吗？')) {
            return;
        }
    }

    isTranscriptEditMode = false;
    transcriptEditDirtyMap.clear();
    updateTranscriptEditToolbar(false);

    // 重新加载会议详情以恢复原始数据
    if (currentMeetingId) {
        selectMeeting(currentMeetingId);
    } else {
        renderTranscripts(currentTranscripts);
    }
}
