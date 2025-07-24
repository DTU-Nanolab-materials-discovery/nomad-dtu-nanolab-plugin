from src.nomad_dtu_nanolab_plugin.schema_packages.rtp import (
    DtuRTP,
    DTURTPSteps,
    DtuRTPSubstrateMounting,
    RTPOverview,
    RTPStepOverview,
)

# Create RTP instance
rtp = DtuRTP()
rtp.lab_id = 'user_001_RTP'
rtp.location = 'DTU; IDOL Lab'
rtp.log_file_eklipse = 'eklipse_log.txt'
rtp.log_file_T2BDiagnostics = 'temp_log.txt'
rtp.samples_susceptor_before = 'before.jpg'
rtp.samples_susceptor_after = 'after.jpg'
rtp.used_gases = ['Ar', 'N2', 'PH3', 'H2S']
rtp.base_pressure = 0.05
rtp.base_pressure_ballast = 0.08
rtp.rate_of_rise = 0.001
rtp.chiller_flow = 0.002

# Add substrate
substrate = DtuRTPSubstrateMounting()
substrate.name = 'bl'
substrate.relative_position = 'bl'
substrate.position_x = 0.02
substrate.position_y = 0.035
substrate.rotation = 0
rtp.substrates = [substrate]

# Add overview
overview = RTPOverview()
overview.material_space = 'Sn-P-S'
overview.annealing_pressure = 100
overview.annealing_time = 600
overview.annealing_temperature = 1073
overview.annealing_Ar_flow = 0.0001
overview.annealing_N2_flow = 0.0001
overview.annealing_PH3_in_Ar_flow = 0.00001
overview.annealing_H2S_in_Ar_flow = 0.00001
overview.total_heating_time = 300
overview.total_cooling_time = 400
overview.end_of_process_temperature = 300
rtp.overview = overview

# Add steps
steps = []
for i, (init_temp, final_temp, duration) in enumerate(
    [
        (300, 800, 120),  # Ramp up
        (800, 800, 600),  # Hold
        (800, 300, 180),  # Ramp down
    ]
):
    step_overview = RTPStepOverview()
    step_overview.initial_temperature = 25
    step_overview.final_temperature = 500
    step_overview.duration = 600
    step_overview.pressure = 90
    step_overview.step_Ar_flow = 0.0001
    step_overview.step_N2_flow = 0.0001
    step_overview.step_PH3_in_Ar_flow = 0.00001
    step_overview.step_H2S_in_Ar_flow = 0.00001
    step = DTURTPSteps()
    step.step_overview = step_overview
    steps.append(step)
rtp.steps = steps


# Dummy archive and logger for normalize
class DummyArchive:
    pass


class DummyLogger:
    def info(self, msg):
        print(msg)

    def warning(self, msg):
        print(msg)

    def error(self, msg):
        print(msg)


rtp.normalize(DummyArchive(), DummyLogger())

# Print results
print('Time array:', rtp.time)
print('Temperature profile:', rtp.temperature_profile)
print('Plotly figure JSON:', rtp.figures[0].figure)
