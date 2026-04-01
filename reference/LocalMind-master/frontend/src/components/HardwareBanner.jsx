import { useState, useEffect } from 'react';
import { Cpu, Zap, Rocket, Monitor, HardDrive, ChevronDown, ChevronUp } from 'lucide-react';
import { getHardwareStatus } from '../api/client';

/**
 * Performance banner showing hardware acceleration status.
 *
 * Displays:
 * - "⚡ Accelerated by Intel Iris Xe" (if OpenVINO is active)
 * - "🚀 Accelerated by NVIDIA [Model]" (if CUDA is active)
 * - "💻 Running on [N] CPU Threads" (as a fallback)
 */
function HardwareBanner() {
  const [hardware, setHardware] = useState(null);
  const [error, setError] = useState(false);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    fetchHardwareStatus();
  }, []);

  async function fetchHardwareStatus() {
    try {
      const data = await getHardwareStatus();
      setHardware(data);
    } catch (err) {
      console.error('Failed to fetch hardware status:', err);
      setError(true);
    }
  }

  if (error || !hardware) {
    return null;
  }

  const gpu = hardware.primary_gpu;
  const cpu = hardware.cpu;
  const memory = hardware.memory;
  const accelerator = gpu?.accelerator;

  // Determine banner style and content based on accelerator
  let bannerConfig;

  if (accelerator === 'nvidia_cuda' && gpu?.is_available) {
    bannerConfig = {
      icon: <Rocket className="w-4 h-4" />,
      emoji: '🚀',
      label: `Accelerated by NVIDIA ${gpu.name}`,
      sublabel: gpu.vram_gb > 0 ? `${gpu.vram_gb.toFixed(1)} GB VRAM` : null,
      bgClass: 'bg-gradient-to-r from-green-50 to-emerald-50 border-green-200',
      textClass: 'text-green-800',
      badgeClass: 'bg-green-100 text-green-700',
      badgeText: 'CUDA',
    };
  } else if (accelerator === 'intel_openvino' && gpu?.is_available) {
    bannerConfig = {
      icon: <Zap className="w-4 h-4" />,
      emoji: '⚡',
      label: `Accelerated by ${gpu.name}`,
      sublabel: 'OpenVINO Runtime',
      bgClass: 'bg-gradient-to-r from-blue-50 to-indigo-50 border-blue-200',
      textClass: 'text-blue-800',
      badgeClass: 'bg-blue-100 text-blue-700',
      badgeText: 'OpenVINO',
    };
  } else if (accelerator === 'amd_rocm' && gpu?.is_available) {
    bannerConfig = {
      icon: <Rocket className="w-4 h-4" />,
      emoji: '🔥',
      label: `Accelerated by AMD ${gpu.name}`,
      sublabel: gpu.vram_gb > 0 ? `${gpu.vram_gb.toFixed(1)} GB VRAM` : null,
      bgClass: 'bg-gradient-to-r from-red-50 to-orange-50 border-red-200',
      textClass: 'text-red-800',
      badgeClass: 'bg-red-100 text-red-700',
      badgeText: 'ROCm',
    };
  } else {
    bannerConfig = {
      icon: <Cpu className="w-4 h-4" />,
      emoji: '💻',
      label: `Running on ${cpu.total_cores} CPU Threads`,
      sublabel: cpu.is_hybrid ? `Hybrid: ${cpu.p_cores}P + ${cpu.e_cores}E cores` : cpu.name,
      bgClass: 'bg-gradient-to-r from-gray-50 to-slate-50 border-gray-200',
      textClass: 'text-gray-700',
      badgeClass: 'bg-gray-100 text-gray-600',
      badgeText: 'CPU',
    };
  }

  return (
    <div className={`border rounded-lg overflow-hidden ${bannerConfig.bgClass}`}>
      {/* Main banner row */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-4 py-2.5 transition-colors hover:opacity-90"
      >
        <div className="flex items-center gap-3">
          <span className="text-base">{bannerConfig.emoji}</span>
          <div className="flex items-center gap-2">
            <span className={`text-sm font-medium ${bannerConfig.textClass}`}>
              {bannerConfig.label}
            </span>
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${bannerConfig.badgeClass}`}>
              {bannerConfig.badgeText}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {bannerConfig.sublabel && (
            <span className={`text-xs ${bannerConfig.textClass} opacity-70 hidden sm:inline`}>
              {bannerConfig.sublabel}
            </span>
          )}
          {expanded ? (
            <ChevronUp className={`w-4 h-4 ${bannerConfig.textClass} opacity-50`} />
          ) : (
            <ChevronDown className={`w-4 h-4 ${bannerConfig.textClass} opacity-50`} />
          )}
        </div>
      </button>

      {/* Expanded details */}
      {expanded && (
        <div className="px-4 pb-3 pt-1 border-t border-opacity-20 border-gray-300">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
            {/* CPU Info */}
            <div className="flex items-start gap-2">
              <Cpu className="w-3.5 h-3.5 text-gray-500 mt-0.5 flex-shrink-0" />
              <div>
                <p className="font-medium text-gray-700">CPU</p>
                <p className="text-gray-500">{cpu.name || 'Unknown'}</p>
                <p className="text-gray-500">
                  {cpu.physical_cores} cores / {cpu.total_cores} threads
                </p>
                {cpu.is_hybrid && (
                  <p className="text-gray-500">
                    {cpu.p_cores}P + {cpu.e_cores}E (Hybrid)
                  </p>
                )}
              </div>
            </div>

            {/* GPU Info */}
            <div className="flex items-start gap-2">
              <Monitor className="w-3.5 h-3.5 text-gray-500 mt-0.5 flex-shrink-0" />
              <div>
                <p className="font-medium text-gray-700">GPU</p>
                {gpu?.is_available ? (
                  <>
                    <p className="text-gray-500">{gpu.name}</p>
                    <p className="text-gray-500">
                      {accelerator === 'nvidia_cuda' && `CUDA • ${gpu.vram_gb.toFixed(1)} GB`}
                      {accelerator === 'intel_openvino' && 'OpenVINO • Shared Memory'}
                      {accelerator === 'amd_rocm' && `ROCm • ${gpu.vram_gb.toFixed(1)} GB`}
                    </p>
                    {gpu.supports_fp16 && (
                      <p className="text-gray-500">FP16 supported</p>
                    )}
                  </>
                ) : (
                  <p className="text-gray-500">No GPU detected</p>
                )}
              </div>
            </div>

            {/* Memory Info */}
            <div className="flex items-start gap-2">
              <HardDrive className="w-3.5 h-3.5 text-gray-500 mt-0.5 flex-shrink-0" />
              <div>
                <p className="font-medium text-gray-700">Memory</p>
                <p className="text-gray-500">
                  {memory.total_gb.toFixed(1)} GB total
                </p>
                <p className="text-gray-500">
                  {memory.available_gb.toFixed(1)} GB available
                </p>
                {memory.is_low_memory && (
                  <p className="text-amber-600 font-medium">⚠ Low memory mode</p>
                )}
              </div>
            </div>
          </div>

          {/* Accelerator priority */}
          {hardware.accelerator_priority && hardware.accelerator_priority.length > 1 && (
            <div className="mt-2 pt-2 border-t border-gray-200 border-opacity-30">
              <p className="text-xs text-gray-500">
                <span className="font-medium">Accelerator priority:</span>{' '}
                {hardware.accelerator_priority
                  .map((a) => {
                    const labels = {
                      nvidia_cuda: 'NVIDIA CUDA',
                      intel_openvino: 'Intel OpenVINO',
                      amd_rocm: 'AMD ROCm',
                      cpu: 'CPU',
                    };
                    return labels[a] || a;
                  })
                  .join(' → ')}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default HardwareBanner;
