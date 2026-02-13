# References

## Characterization Methods

| Method | Machine Supplier | Proprietary File | Manual export | Plugin Class | Comment |
|--------|------------------|------------------|-----------------|--------------|---------|
| **X-Ray Diffraction (XRD)** | Rigaku | [.rasx](https://github.com/DTU-Nanolab-materials-discovery/nomad-dtu-nanolab-plugin/blob/main/tests/data/ZnO_XRD_map/ZnO%20ALD%20training_001_1_0-000_0-000.rasx) | - | `DTUXRDMeasurement` | Each file is a single measurement |
| **Energy Dispersive X-Ray Spectroscopy (EDX)** | ? | ? | [.xlsx](https://github.com/DTU-Nanolab-materials-discovery/nomad-dtu-nanolab-plugin/blob/main/tests/data/mittma_00012_FR.xlsx) | `DTUEDXMeasurement` | The .xlsx contains the elemental composition data and corner positions |
| **Raman Spectroscopy** | Renishaw | [.wdf](https://github.com/DTU-Nanolab-materials-discovery/nomad-dtu-nanolab-plugin/blob/main/tests/data/indiogo_0019_RTP_hc_1x10s_P1_x20_map_0.wdf) | - | `DTURamanMeasurement` | - |
| **Spectroscopic Ellipsometry** | J.A. Woollam | ? | [.txt](https://github.com/DTU-Nanolab-materials-discovery/nomad-dtu-nanolab-plugin/blob/main/tests/data/eugbe_0009_RTP_hc_SiO2_map_nk_vs_energy.txt) | `DTUEllipsometryMeasurement` | - |
