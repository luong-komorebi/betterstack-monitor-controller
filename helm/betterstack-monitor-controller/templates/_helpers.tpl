{{/*
Expand the name of the chart.
*/}}
{{- define "betterstack-monitor-controller.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "betterstack-monitor-controller.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart label.
*/}}
{{- define "betterstack-monitor-controller.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels.
*/}}
{{- define "betterstack-monitor-controller.labels" -}}
helm.sh/chart: {{ include "betterstack-monitor-controller.chart" . }}
{{ include "betterstack-monitor-controller.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels.
*/}}
{{- define "betterstack-monitor-controller.selectorLabels" -}}
app.kubernetes.io/name: {{ include "betterstack-monitor-controller.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
ServiceAccount name.
*/}}
{{- define "betterstack-monitor-controller.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "betterstack-monitor-controller.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Secret name that holds the BetterStack API token.
Prefers an existing secret if configured; otherwise uses the chart-managed secret.
*/}}
{{- define "betterstack-monitor-controller.secretName" -}}
{{- if .Values.existingSecret.name }}
{{- .Values.existingSecret.name }}
{{- else }}
{{- include "betterstack-monitor-controller.fullname" . }}
{{- end }}
{{- end }}

{{/*
Key inside the Secret that holds the API token.
*/}}
{{- define "betterstack-monitor-controller.secretKey" -}}
{{- default "api-token" .Values.existingSecret.key }}
{{- end }}

{{/*
Resolved image tag — falls back to .Chart.AppVersion.
*/}}
{{- define "betterstack-monitor-controller.imageTag" -}}
{{- default .Chart.AppVersion .Values.image.tag }}
{{- end }}
