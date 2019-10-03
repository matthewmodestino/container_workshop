# install_uf.ps1 - install Splunk Univeral forwarder script.

Param(
    [string]$HostFile
)

if (!$HostFile) {
    Write-Host '[*] Install Splunk Universal Forwarder on localhost'
    $params = @{ReceivingIndexer=$env:SPLUNK_URL;splunk_home=$env:SPLUNK_HOME;dimensions=$env:DIMENSIONS;log_sources_param=$env:LOG_SOURCES;metrics_param=$env:METRICS;per_cpu=$env:PER_CPU;metrics_index=$env:METRICS_INDEX;receiver_port=$env:RECEIVER_PORT}
	& ".\install_uf_script.ps1" @params
} else {
    # if $HostFile is not specified, then
    if (!(Test-Path $HostFile)) {
        echo "file: $HostFile does not exist"
        exit(0)
    }

    # read host list from $HostFile
    [array]$host_list = Get-Content $HostFile

    # remote execute the installation script
    foreach ($h in $host_list) {
        Write-Host '[*] Install Splunk Universal Forwarder remotely on' $h
        Invoke-Command -FilePath install_uf_script.ps1 -ArgumentList $env:SPLUNK_URL,$env:SPLUNK_HOME,$env:DIMENSIONS,$env:LOG_SOURCES,$env:METRICS,$env:PER_CPU,$env:METRICS_INDEX,$env:RECEIVER_PORT -ComputerName $h

        Write-Host '[*] ----------------------------------------'
    }
}
