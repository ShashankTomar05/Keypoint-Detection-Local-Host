import { useState } from "react";
import "@/App.css";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "sonner";
import axios from "axios";
import {
  Upload,
  Download,
  Image as ImageIcon,
  FileJson,
  Loader2,
  ScanSearch,
  Sparkles,
  Users,
  Workflow,
  BadgeCheck,
} from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";
const API = `${BACKEND_URL}/api`;

const featureCards = [
  {
    icon: Users,
    title: "Multi-person aware",
    description: "Detect several people in the same image and keep each pose grouped cleanly.",
  },
  {
    icon: Workflow,
    title: "Animation-ready export",
    description: "Download JSON and annotated previews for Blender, Adobe Animate, or review workflows.",
  },
  {
    icon: BadgeCheck,
    title: "Confidence filtered",
    description: "Surface stronger landmarks first while preserving weaker poses when the scene gets crowded.",
  },
];

const quickStats = [
  { label: "Pose Model", value: "33 points" },
  { label: "Use Case", value: "Images" },
  { label: "Export", value: "JSON + JPG" },
];

function App() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [loading, setLoading] = useState(false);
  const [detectionResult, setDetectionResult] = useState(null);
  const [annotatedImageUrl, setAnnotatedImageUrl] = useState(null);

  const handleFileSelect = (event) => {
    const file = event.target.files[0];
    if (file) {
      if (!file.type.startsWith("image/")) {
        toast.error("Please select a valid image file");
        return;
      }

      setSelectedFile(file);
      setPreviewUrl(URL.createObjectURL(file));
      setDetectionResult(null);
      setAnnotatedImageUrl(null);
    }
  };

  const handleDetectPose = async () => {
    if (!selectedFile) {
      toast.error("Please select an image first");
      return;
    }

    setLoading(true);
    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      const response = await axios.post(`${API}/detect-pose`, formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });

      setDetectionResult(response.data);
      setAnnotatedImageUrl(`${API}/download/${response.data.detection_id}/image`);
      toast.success("Detection completed successfully");
    } catch (error) {
      console.error("Error detecting pose:", error);
      toast.error(error.response?.data?.detail || "Failed to detect pose. Please try another image.");
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadJSON = () => {
    if (detectionResult) {
      window.open(`${API}/download/${detectionResult.detection_id}/json`, "_blank");
      toast.success("JSON file download started");
    }
  };

  const handleDownloadImage = () => {
    if (detectionResult) {
      window.open(`${API}/download/${detectionResult.detection_id}/image`, "_blank");
      toast.success("Annotated image download started");
    }
  };

  return (
    <div className="App min-h-screen">
      <div className="app-shell">
        <div className="app-orb app-orb-one" />
        <div className="app-orb app-orb-two" />

        <header className="border-b border-white/40 bg-white/60 backdrop-blur-xl">
          <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-5 lg:px-10">
            <div className="flex items-center gap-4">
              <div className="brand-mark">
                <ScanSearch className="h-6 w-6 text-white" />
              </div>
              <div>
                <p className="font-display text-2xl font-bold tracking-tight text-slate-900">
                  Keypoint Detection System
                </p>
                <p className="text-sm text-slate-600">MediaPipe-powered pose extraction for multi-person scenes</p>
              </div>
            </div>

            <div className="hidden items-center gap-3 rounded-full border border-slate-200 bg-white/80 px-4 py-2 text-sm text-slate-600 shadow-sm md:flex">
              <Sparkles className="h-4 w-4 text-amber-500" />
              Ready for dense group shots
            </div>
          </div>
        </header>

        <main className="mx-auto flex max-w-7xl flex-col gap-10 px-6 py-10 lg:px-10 lg:py-12">
          <section className="hero-panel">
            <div className="grid gap-10 lg:grid-cols-[1.25fr_0.9fr] lg:items-end">
              <div className="space-y-6">
                <div className="inline-flex items-center gap-2 rounded-full border border-cyan-200 bg-cyan-50 px-4 py-2 text-sm font-medium text-cyan-800">
                  <Sparkles className="h-4 w-4" />
                  Refined workspace for pose detection
                </div>

                <div className="space-y-4">
                  <h1 className="font-display text-4xl font-bold leading-tight text-slate-950 md:text-5xl">
                    Turn still images into a cleaner, more useful pose analysis dashboard.
                  </h1>
                  <p className="max-w-2xl text-lg leading-8 text-slate-600">
                    Upload a single frame, detect all visible people, preview the annotated result, and export files
                    for animation or downstream tooling without the cramped student-project look.
                  </p>
                </div>

                <div className="grid gap-3 sm:grid-cols-3">
                  {quickStats.map((item) => (
                    <div key={item.label} className="hero-stat">
                      <p className="text-xs uppercase tracking-[0.24em] text-slate-500">{item.label}</p>
                      <p className="mt-2 font-display text-2xl font-bold text-slate-900">{item.value}</p>
                    </div>
                  ))}
                </div>
              </div>

              <div className="hero-info-card">
                <div className="space-y-5">
                  <div>
                    <p className="text-sm font-semibold uppercase tracking-[0.22em] text-slate-500">Workflow</p>
                    <h2 className="mt-2 font-display text-2xl font-bold text-slate-950">Fast upload, visual review, export</h2>
                  </div>

                  <div className="space-y-3">
                    {featureCards.map(({ icon: Icon, title, description }) => (
                      <div key={title} className="feature-row">
                        <div className="feature-icon">
                          <Icon className="h-5 w-5" />
                        </div>
                        <div>
                          <p className="font-semibold text-slate-900">{title}</p>
                          <p className="text-sm leading-6 text-slate-600">{description}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </section>

          <section className="grid gap-8 xl:grid-cols-[0.95fr_1.05fr]">
            <Card className="panel-card overflow-hidden border-0">
              <CardHeader className="panel-header">
                <div className="panel-badge">
                  <Upload className="h-4 w-4" />
                  Input
                </div>
                <CardTitle className="font-display text-3xl text-slate-950">Upload your image</CardTitle>
                <CardDescription className="max-w-xl text-base leading-7 text-slate-600">
                  Pick any JPG or PNG containing one or more people. We&apos;ll process the frame and return grouped
                  pose data plus an annotated preview.
                </CardDescription>
              </CardHeader>

              <CardContent className="space-y-6">
                <div className="upload-dropzone">
                  <input
                    type="file"
                    accept="image/*"
                    onChange={handleFileSelect}
                    className="hidden"
                    id="file-upload"
                    data-testid="file-upload-input"
                  />
                  <label htmlFor="file-upload" className="upload-dropzone-label">
                    <div className="upload-icon-shell">
                      <Upload className="h-9 w-9 text-cyan-700" />
                    </div>
                    <div className="space-y-2">
                      <p className="font-display text-3xl font-bold text-slate-950">Drop image or click to browse</p>
                      <p className="text-base text-slate-600">Supports PNG, JPG and JPEG. Best results come from full-body or mid-body shots.</p>
                    </div>
                  </label>
                </div>

                {previewUrl ? (
                  <div className="space-y-5">
                    <div className="preview-frame">
                      <div className="preview-frame-header">
                        <span className="preview-chip">Original frame</span>
                        <span className="text-sm text-slate-500">{selectedFile?.name}</span>
                      </div>
                      <img src={previewUrl} alt="Preview" className="preview-image" data-testid="preview-image" />
                    </div>

                    <Button
                      onClick={handleDetectPose}
                      disabled={loading}
                      className="detect-button"
                      data-testid="detect-pose-button"
                    >
                      {loading ? (
                        <>
                          <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                          Detecting people...
                        </>
                      ) : (
                        <>
                          <ScanSearch className="mr-2 h-5 w-5" />
                          Detect all visible people
                        </>
                      )}
                    </Button>
                  </div>
                ) : (
                  <div className="grid gap-4 sm:grid-cols-3">
                    {featureCards.map(({ icon: Icon, title, description }) => (
                      <div key={title} className="mini-feature-card">
                        <Icon className="h-5 w-5 text-cyan-700" />
                        <p className="mt-4 font-semibold text-slate-900">{title}</p>
                        <p className="mt-2 text-sm leading-6 text-slate-600">{description}</p>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            <Card className="panel-card overflow-hidden border-0">
              <CardHeader className="panel-header">
                <div className="panel-badge panel-badge-warm">
                  <ImageIcon className="h-4 w-4" />
                  Output
                </div>
                <CardTitle className="font-display text-3xl text-slate-950">Detection results</CardTitle>
                <CardDescription className="max-w-xl text-base leading-7 text-slate-600">
                  Review the annotated image, confirm how many people were found, and export the structured files.
                </CardDescription>
              </CardHeader>

              <CardContent className="space-y-6">
                {!detectionResult ? (
                  <div className="results-empty-state">
                    <div className="results-empty-icon">
                      <ImageIcon className="h-10 w-10" />
                    </div>
                    <div className="space-y-2">
                      <p className="font-display text-2xl font-bold text-slate-900">No analysis yet</p>
                      <p className="mx-auto max-w-md text-sm leading-6 text-slate-600">
                        Upload a frame and run detection to see pose overlays, people counts, and export actions here.
                      </p>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-6">
                    {annotatedImageUrl && (
                      <div className="preview-frame">
                        <div className="preview-frame-header">
                          <span className="preview-chip preview-chip-warm">Annotated output</span>
                          <span className="text-sm text-slate-500">Detection ready</span>
                        </div>
                        <img
                          src={annotatedImageUrl}
                          alt="Detected Pose"
                          className="preview-image"
                          data-testid="annotated-image"
                        />
                      </div>
                    )}

                    <div className="stats-grid">
                      <div className="metric-card metric-card-amber">
                        <p className="metric-value">{detectionResult.people_count ?? 1}</p>
                        <p className="metric-label">People detected</p>
                      </div>
                      <div className="metric-card metric-card-cyan">
                        <p className="metric-value">{detectionResult.keypoints_count}</p>
                        <p className="metric-label">Reliable keypoints</p>
                      </div>
                      <div className="metric-card metric-card-emerald">
                        <p className="metric-value">{detectionResult.model_keypoints_per_person ?? 33}</p>
                        <p className="metric-label">Landmarks per person</p>
                      </div>
                    </div>

                    <div className="result-note">
                      <BadgeCheck className="h-4 w-4 shrink-0 text-emerald-600" />
                      <p className="text-sm leading-6 text-slate-700">
                        Showing reliable landmarks across detected people
                        {detectionResult.visibility_threshold
                          ? ` with visibility >= ${detectionResult.visibility_threshold}.`
                          : "."}
                      </p>
                    </div>

                    <div className="grid gap-3 sm:grid-cols-2">
                      <Button
                        onClick={handleDownloadJSON}
                        variant="outline"
                        className="download-button"
                        data-testid="download-json-button"
                      >
                        <FileJson className="mr-2 h-4 w-4" />
                        Download JSON
                      </Button>
                      <Button
                        onClick={handleDownloadImage}
                        variant="outline"
                        className="download-button"
                        data-testid="download-image-button"
                      >
                        <Download className="mr-2 h-4 w-4" />
                        Download image
                      </Button>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </section>

          <section className="grid gap-6 md:grid-cols-3">
            {featureCards.map(({ icon: Icon, title, description }) => (
              <Card key={title} className="insight-card border-0">
                <CardHeader>
                  <div className="feature-icon mb-4">
                    <Icon className="h-5 w-5" />
                  </div>
                  <CardTitle className="font-display text-2xl text-slate-950">{title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm leading-7 text-slate-600">{description}</p>
                </CardContent>
              </Card>
            ))}
          </section>
        </main>
      </div>
    </div>
  );
}

export default App;
