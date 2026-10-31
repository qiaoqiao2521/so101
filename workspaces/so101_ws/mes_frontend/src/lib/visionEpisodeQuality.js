const EMPTY_COUNT = 0;

function asObject(value) {
  return value && typeof value === 'object' && !Array.isArray(value) ? value : {};
}

function asCount(value) {
  const count = Number(value);
  return Number.isFinite(count) && count >= 0 ? count : EMPTY_COUNT;
}

function firstText(...values) {
  return values.find((value) => typeof value === 'string' && value.trim())?.trim() || '';
}

function normalizeStatus(status) {
  const value = String(status || '').trim().toLowerCase();
  if (['passed', 'pass', 'ok', 'success', 'done'].includes(value)) {
    return 'passed';
  }
  if (['warn', 'warning'].includes(value)) {
    return 'warn';
  }
  if (['failed', 'fail', 'error'].includes(value)) {
    return 'failed';
  }
  if (['blocked', 'not_available'].includes(value)) {
    return 'blocked';
  }
  return 'unknown';
}

function sumHeartbeatEvents(statusEvents = []) {
  if (!Array.isArray(statusEvents)) {
    return 0;
  }
  return statusEvents.reduce((total, event) => total + asCount(event?.heartbeatCount), 0);
}

export function normalizeVisionEpisodeQuality(input = {}, options = {}) {
  const source = asObject(input);
  const episodeManifest = asObject(source.episodeManifest || source.manifest);
  const datasetIndex = asObject(source.datasetIndex || source.dataset);
  const candidateManifest = asObject(source.candidateManifest || source.candidate);
  const validationReport = asObject(source.validationReport);
  const datasetValidation = asObject(datasetIndex.validation);
  const candidatePaths = asObject(candidateManifest.paths);
  const artifactPaths = asObject(source.paths);
  const nativeLeRobot = asObject(candidateManifest.native_lerobot || candidateManifest.nativeLeRobot || source.nativeLeRobot);
  const yoloSmoke = asObject(source.yoloSmoke);
  const yoloWeights = asObject(yoloSmoke.weights);
  const yoloPredict = asObject(yoloSmoke.predict);

  const status = normalizeStatus(
    firstText(
      source.datasetValidationStatus,
      datasetValidation.status,
      validationReport.status,
      source.validationStatus,
      nativeLeRobot.status,
      yoloSmoke.status,
    ),
  );
  const candidateManifestPath = firstText(
    source.candidateManifestPath,
    artifactPaths.candidateManifest,
    candidateManifest.manifest_path,
    candidateManifest.manifestPath,
    candidatePaths.manifest,
  );
  const nativePath = firstText(source.nativeLeRobotPath, artifactPaths.nativeLeRobot, nativeLeRobot.native_dataset_root);
  const yoloSmokePath = firstText(source.yoloSmokePath, artifactPaths.yoloSmoke);
  const yoloBestWeightPath = firstText(yoloWeights.best);
  const nativeReason = firstText(
    source.nativeLeRobotBlockedReason,
    nativeLeRobot.reason,
    nativeLeRobot.blocked_reason,
    nativeLeRobot.blockedReason,
  );
  const heartbeatCount = asCount(
    source.heartbeatCount ??
      source.taskStatusHeartbeatCount ??
      source.task_status_heartbeat_count ??
      sumHeartbeatEvents(options.statusEvents),
  );
  const sampleCount = asCount(source.sampleCount ?? candidateManifest.sample_count ?? datasetIndex.sample_count);
  const trainCount = asCount(source.trainCount ?? candidateManifest.train_sample_count);
  const debugCount = asCount(source.debugCount ?? candidateManifest.debug_sample_count);
  const rejectedCount = asCount(source.rejectedCount ?? candidateManifest.rejected_sample_count);
  const missing = asObject(datasetValidation.missing);
  const largeDelta = asObject(datasetValidation.large_delta || datasetValidation.largeDelta);

  const hasInjectedData = Boolean(
    source.episodeId ||
      episodeManifest.episode_id ||
      datasetIndex.source_episode_id ||
      candidateManifest.source_episode_id ||
      sampleCount ||
      candidateManifestPath ||
      source.datasetValidationStatus ||
      datasetValidation.status ||
      validationReport.status ||
      nativeLeRobot.status ||
      yoloSmoke.status,
  );
  const yoloSmokeStatus = normalizeStatus(yoloSmoke.status);
  const yoloTrain = asObject(yoloSmoke.train);
  const yoloResults = asObject(yoloTrain.results_dict || yoloTrain.resultsDict);

  return {
    hasData: hasInjectedData,
    episodeId: firstText(
      source.episodeId,
      episodeManifest.episode_id,
      datasetIndex.source_episode_id,
      candidateManifest.source_episode_id,
    ),
    datasetValidationStatus: status,
    datasetValidationLabel: {
      passed: 'passed',
      warn: 'warn',
      failed: 'failed',
      blocked: 'blocked',
      unknown: 'no report',
    }[status],
    sampleCount,
    trainCount,
    debugCount,
    rejectedCount,
    heartbeatCount,
    candidateManifestPath,
    nativeLeRobotPath: nativePath,
    nativeLeRobotAvailable: nativeLeRobot.available === true || nativeLeRobot.status === 'done',
    nativeLeRobotStatus: nativeLeRobot.status || (nativeLeRobot.available === true ? 'available' : nativeLeRobot.available === false ? 'blocked' : ''),
    nativeLeRobotBlockedReason: nativeLeRobot.available === false ? nativeReason || 'native LeRobot writer unavailable' : nativeReason,
    yoloSmokeStatus,
    yoloSmokeLabel: {
      passed: 'done',
      warn: 'warn',
      failed: 'failed',
      blocked: 'blocked',
      unknown: 'no smoke',
    }[yoloSmokeStatus],
    yoloSmokePath,
    yoloBestWeightPath,
    yoloPredictCount: asCount(yoloPredict.result_count ?? yoloPredict.resultCount),
    yoloPredictBoxCount: asCount(yoloPredict.first_box_count ?? yoloPredict.firstBoxCount),
    yoloMap50: Number(yoloResults['metrics/mAP50(B)'] ?? yoloResults.map50 ?? 0),
    validationNote: buildValidationNote({ status, missing, largeDelta }),
  };
}

export function buildVisionEpisodeQualityCards(quality) {
  const model = normalizeVisionEpisodeQuality(quality);
  return [
    {
      label: 'Dataset validation',
      value: model.datasetValidationLabel,
      tone: `quality-${model.datasetValidationStatus}`,
      note: model.validationNote,
    },
    {
      label: 'Train',
      value: String(model.trainCount),
      tone: 'quality-passed',
      note: `${model.sampleCount} total samples`,
    },
    {
      label: 'Debug',
      value: String(model.debugCount),
      tone: model.debugCount ? 'quality-warn' : 'quality-passed',
      note: 'warn samples stay out of train by default',
    },
    {
      label: 'Rejected',
      value: String(model.rejectedCount),
      tone: model.rejectedCount ? 'quality-failed' : 'quality-passed',
      note: 'failed samples are excluded',
    },
    {
      label: 'Heartbeat',
      value: String(model.heartbeatCount),
      tone: model.heartbeatCount ? 'quality-passed' : 'quality-unknown',
      note: 'task status heartbeat count in latest view',
    },
    {
      label: 'YOLO smoke',
      value: model.yoloSmokeLabel,
      tone: `quality-${model.yoloSmokeStatus}`,
      note: model.yoloSmokeStatus === 'passed'
        ? `predict ${model.yoloPredictCount}, boxes ${model.yoloPredictBoxCount}`
        : 'waiting for train/predict smoke report',
    },
  ];
}

function buildValidationNote({ status, missing, largeDelta }) {
  if (status === 'unknown') {
    return 'waiting for dataset-index or validation-report data';
  }
  const missingTotal = Object.values(missing).reduce((total, value) => total + asCount(value), 0);
  const largeDeltaTotal = Object.values(largeDelta).reduce((total, value) => total + asCount(value), 0);
  if (missingTotal || largeDeltaTotal) {
    return `missing ${missingTotal}, large delta ${largeDeltaTotal}`;
  }
  return status === 'passed' ? 'all required stream alignments passed' : 'see validator report for details';
}
