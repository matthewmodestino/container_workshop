# currently must be 'runas' administrator for proper install

Param(
    [string]$ReceivingIndexer,
    [string]$splunk_home,
    [string]$dimensions,
    [string]$log_sources_param,
    [string]$metrics_param,
    [string]$per_cpu,
    [string]$metrics_index,
    [string]$receiver_port
)

# if splunk_home not provided, use default
if([string]::IsNullOrEmpty($splunk_home)) {
  $splunk_home = "$env:programfiles\SplunkUniversalForwarder"
}

if([string]::IsNullOrEmpty($metrics_index)) {
  $metrics_index = 'em_metrics'
}

if([string]::IsNullOrEmpty($receiver_port)) {
  $receiver_port = '9997'
}

# URI to download the install file
$insturi = 'https://www.splunk.com/bin/splunk/DownloadActivityServlet?architecture=x86_64&platform=windows&version=7.2.4&product=universalforwarder&filename=splunkforwarder-7.2.4-8a94541dcfac-x64-release.msi&wget=true'

# directory for file to be downloaded to:
# currently set to download in the path that the script is in:
$path = Convert-Path .
$outputdir = $path + '\splunkuniversalforwarder.msi'

# file name of .msi installation file
$install_file = 'splunkuniversalforwarder.msi'

# hostname or ip : port of indexer
$indexer = $ReceivingIndexer+':'+$receiver_port
echo "[*] indexer server: $indexer"

# Installation Directory for UniversalForwarder
$installdir = $splunk_home

echo "[*] checking for previous installations of splunk>..."

# checks to see if a splunk folder already exists in Program Files
# will skip installation if it finds a splunk folder

if (Test-Path -Path $installdir -PathType Container)
{
    echo "[!] install directory already exists. continuing to congure .."
}else{
    echo "[*] downloading splunk> universal forwarder..."

    # downloads splunk install file
    # this method significantly faster than Invoke-WebRequest
    (New-Object System.Net.WebClient).DownloadFile($insturi, $outputdir)

    # check if download succedded
    if (-not $?)
    {
        echo "[!] failed to download splunk> universal forwarder..."
        exit 1
    }

    echo "[*] installing splunk> universal fowarder..."

    # uses msi to install splunk forwarder, file names need to match and be co-located
    # /quiet suppresses gui, otherwise the script will fail
    # additional switches would be needed for an enterprise installation
    # testing on whether local user can collect log files (i believe no)
    # might need to be installed as a domain user or local admin?
    # see: <https://docs.splunk.com/Documentation/Forwarder/6.5.1/Forwarder/InstallaWindowsuniversalforwarderfromthecommandline>
    # for supported switches and installation instructions
    Start-Process -FilePath msiexec.exe -ArgumentList "/i $install_file INSTALLDIR=`"$installdir`" AGREETOLICENSE=Yes /quiet" -Wait
}

# **********  Configure Outputs.conf file in SplunkUniversalForwarder local Dirctory  ************

# location of outputs.conf file
$outputsconf = $splunk_home + "\etc\apps\SplunkUniversalForwarder\local\outputs.conf"
echo "[tcpout]" > $outputsconf
echo "defaultGroup = default-autolb-group" >> $outputsconf
echo "" >> $outputsconf
echo "[tcpout:default-autolb-group]" >> $outputsconf
echo "server = $indexer" >> $outputsconf
echo "" >> $outputsconf

# **********  Configure Inputs.conf file in SplunkUniversalForwarder local Dirctory  ************

# location of inputs.conf file
$inputconf = $splunk_home + "\etc\apps\SplunkUniversalForwarder\local\inputs.conf"


# check if supported environment variables set, use default if not
# If not set, use the default value
if([string]::IsNullOrEmpty($metrics_param)) {
  $metrics_param = "logical_disk,physical_disk,cpu,memory,network,system,process"
}

if([string]::IsNullOrEmpty($log_sources_param)) {
  $log_sources_param = "application%WinEventLog,system%WinEventLog,security%WinEventLog"
}

if([string]::IsNullOrEmpty($per_cpu)) {
  $per_cpu = "false"
}

# check if cpu metrics collected per cpu or total
if ($env:per_cpu -eq "true") {$cpu_instance_type = '*'}
else {$cpu_instance_type = '_Total'}

# Set instance_id and account_id depending on CLOUD env variable.
if ($env:CLOUD -eq "AWS") {
  $instance_id = Invoke-RestMethod -Uri http://169.254.169.254/latest/meta-data/instance-id
  $account_id = (Invoke-RestMethod -Uri http://169.254.169.254/latest/meta-data/identity-credentials/ec2/info/).accountId
  if ([string]::IsNullOrEmpty($instance_id) -or [string]::IsNullOrEmpty($account_id)) {
      echo "Please configure Cloud Type, AWS instance ID and AWS Account ID manually in inputs.conf under the respective log sources as follows: _meta = cloud::AWS instanceid::<instance_id> accountid::<account_id>"
  }
}

# Inputs.conf stanza for the supported metrics
$m_cpu =`
"[perfmon://CPU]`r`n" `
+ "counters = % C1 Time;% C2 Time;% Idle Time;% Processor Time;% User Time;% Privileged Time;% Reserved Time;% Interrupt Time`r`n" `
+ "instances = $cpu_instance_type`r`n" `
+ "interval = 60`r`n" `
+ "object = Processor`r`n" `
+ "mode = single`r`n" `
+ "useEnglishOnly = true`r`n" `
+ "sourcetype = PerfmonMetrics:CPU`r`n" `
+ "index = $metrics_index"

$m_memory =`
"[perfmon://Memory]`r`n" `
+ "counters = Cache Bytes;% Committed Bytes In Use;Page Reads/sec;Pages Input/sec;Pages Output/sec;Committed Bytes;Available Bytes`r`n" `
+ "interval = 60`r`n" `
+ "object = Memory`r`n" `
+ "mode = single`r`n" `
+ "useEnglishOnly = true`r`n" `
+ "sourcetype = PerfmonMetrics:Memory`r`n" `
+ "index = $metrics_index"

$m_physical_disk =`
"[perfmon://PhysicalDisk]`r`n" `
+ "counters = % Disk Read Time;% Disk Write Time`r`n" `
+ "instances = *`r`n" `
+ "interval = 60`r`n" `
+ "object = PhysicalDisk`r`n" `
+ "mode = single`r`n" `
+ "useEnglishOnly = true`r`n" `
+ "sourcetype = PerfmonMetrics:PhysicalDisk`r`n" `
+ "index = $metrics_index"

$m_logical_disk =`
"[perfmon://LogicalDisk]`r`n" `
+ "counters = Free Megabytes;% Free Space`r`n" `
+ "instances = *`r`n" `
+ "interval = 60`r`n" `
+ "object = LogicalDisk`r`n" `
+ "mode = single`r`n" `
+ "useEnglishOnly = true`r`n" `
+ "sourcetype = PerfmonMetrics:LogicalDisk`r`n" `
+ "index = $metrics_index"

$m_network =`
"[perfmon://Network]`r`n" `
+ "counters = Bytes Received/sec;Bytes Sent/sec;Packets Received/sec;Packets Sent/sec;Packets Received Errors;Packets Outbound Errors`r`n" `
+ "instances = *`r`n" `
+ "interval = 60`r`n" `
+ "mode = single`r`n" `
+ "object = Network Interface`r`n" `
+ "useEnglishOnly = true`r`n" `
+ "sourcetype = PerfmonMetrics:Network`r`n" `
+ "index = $metrics_index"

$m_system =`
"[perfmon://System]`r`n" `
+ "counters = Processor Queue Length;Threads;System Up Time`r`n" `
+ "instances = *`r`n" `
+ "interval = 60`r`n" `
+ "object = System`r`n" `
+ "mode = single`r`n" `
+ "useEnglishOnly = true`r`n" `
+ "sourcetype = PerfmonMetrics:System`r`n" `
+ "index = $metrics_index"

$m_process =`
"[perfmon://Process]`r`n" `
+ "counters = % Processor Time;% User Time;% Privileged Time`r`n" `
+ "instances = *`r`n" `
+ "interval = 60`r`n" `
+ "object = Process`r`n" `
+ "mode = single`r`n" `
+ "useEnglishOnly = true`r`n" `
+ "sourcetype = PerfmonMetrics:Process`r`n" `
+ "index = $metrics_index"

# Inputs.conf options for the supported Windows EventLogs
if([string]::IsNullOrEmpty($Env:CLOUD) -or [string]::IsNullOrEmpty($instance_id) -or [string]::IsNullOrEmpty($account_id))
{
    $eventlog_options =`
    "checkpointInterval = 10`r`n" `
    + "current_only = 0`r`n" `
    + "disabled = 0`r`n" `
    + "start_from = oldest"
}
elseif ($env:CLOUD -eq "AWS") {
    $eventlog_options =`
    "checkpointInterval = 10`r`n" `
    + "current_only = 0`r`n" `
    + "disabled = 0`r`n" `
    + "start_from = oldest`r`n" `
    + "_meta = cloud::$Env:CLOUD instanceid::$instance_id accountid::$account_id"
}

# extract os & ip info
$os_info = Get-CimInstance Win32_OperatingSystem | Select-Object Caption, Version
$ip_info = Test-Connection -ComputerName $env:computername -count 1 | Select-Object IPV4Address

# Add OS & ip info as dimension
# If these dimensions are to be updated, user has to rerun this script
$dims = $dimensions + " os::" + "`"" + $os_info.Caption + "`""
$dims = $dims + " os_version::" + $os_info.Version
$dims = $dims + " ip::" + "`"" + $ip_info.IPV4Address.IPAddressToString + "`""
$dims = $dims + ' entity_type::Windows_Host'

$metrics = $metrics_param -split ','
$log_sources = $log_sources_param -split ','

echo "[*] configuring metrics & log inputs..."
echo "# *** Configure Metrics & Logs collected ***" > $inputconf

# Add all other perfmon metrics
For ($i=0; $i -lt $metrics.Length; $i++) {
  $m_name = "m_" + $metrics[$i]
  Get-Variable -Name $m_name -ValueOnly -ErrorAction 'Ignore' >> $inputconf
  # Add dimensions
  echo "_meta = $dims" >> $inputconf
  echo "`n" >> $inputconf
}

# Add other log sources stanza
For ($i=0; $i -lt $log_sources.Length; $i++) {
  if([string]::IsNullOrEmpty($log_sources[$i])) { continue }
  # split log source into source and sourcetype
  $logsource = $log_sources[$i] -split '%'
  if ($logsource.Length -ne 2) { continue }

  $log_source = $($logsource[0])
  $log_sourcetype = $($logsource[1])

  if ($log_sourcetype -eq 'WinEventLog') {
    #Get-Variable -Name $log_source -ValueOnly -ErrorAction 'Ignore' >> $inputconf
    echo "[WinEventLog://$log_source]" >> $inputconf
    echo "$eventlog_options" >> $inputconf
    echo "`r`n" >> $inputconf
  }
  else {
    echo "[monitor://$log_source]" >> $inputconf
    echo "sourcetype = $log_sourcetype" >> $inputconf
    echo "disabled = false" >> $inputconf
    if ($log_sourcetype -eq 'collectd' -Or $log_sourcetype -eq 'uf') {
      echo "index = _internal" >> $inputconf
    }
    echo "`r`n" >> $inputconf
  }
}

# **********  Start Splunk and check if process started  *****************

# restart splunk universal forwarder
$splunkexe = $splunk_home + "\bin\splunk.exe"
echo "[*] Restarting splunk> universal fowarder"
& "$splunkexe" restart

# checks to see if splunkd is running which indicates good install
# then adds the necessary lines to input.conf to retreive powershell logs
$splunk = Get-Process -Name "splunkd" -ErrorAction SilentlyContinue

if ($splunk -ne $null)  # confirms if it restarted successfully
{
    echo "[*] splunk> successfully started."
    echo "[*] running clean up."

    if (Test-Path -Path $install_file)
    {
        Remove-Item $install_file
    }

    echo "[*] clean up complete. Exiting..."
    return
}else{
    echo '[!] splunk process not running!'
    echo '[!] check to make sure installation was successful.'
    return
}

