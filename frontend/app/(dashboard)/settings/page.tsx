"use client";

import { useState } from "react";
import {
  User,
  Shield,
  Bell,
  Key,
  Palette,
  Globe,
  Save,
  Camera,
  Eye,
  EyeOff,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { PageHeader } from "@/components/shared/page-header";
import { useToast } from "@/hooks/use-toast";
import { useAuthStore } from "@/lib/stores/auth-store";

export default function SettingsPage() {
  const { toast } = useToast();
  const user = useAuthStore((state) => state.user);
  const [isSaving, setIsSaving] = useState(false);
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);

  // Derive first_name and last_name from full_name if not present
  const nameParts = user?.full_name?.split(' ') || [];
  const firstName = user?.first_name || nameParts[0] || '';
  const lastName = user?.last_name || nameParts.slice(1).join(' ') || '';

  // Profile form state
  const [profileForm, setProfileForm] = useState({
    first_name: firstName,
    last_name: lastName,
    email: user?.email || "",
  });

  // Password form state
  const [passwordForm, setPasswordForm] = useState({
    current_password: "",
    new_password: "",
    confirm_password: "",
  });

  // Notification settings
  const [notifications, setNotifications] = useState({
    email_critical: true,
    email_high: true,
    email_medium: false,
    email_scan_complete: true,
    push_enabled: false,
    daily_digest: true,
    weekly_report: true,
  });

  // Security settings
  const [security, setSecurity] = useState({
    two_factor: false,
    session_timeout: "30",
    ip_whitelist: "",
  });

  // Appearance settings
  const [appearance, setAppearance] = useState({
    theme: "dark",
    language: "es",
    timezone: "America/Mexico_City",
    date_format: "DD/MM/YYYY",
  });

  const handleSaveProfile = async () => {
    setIsSaving(true);
    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 1000));
    setIsSaving(false);
    toast({
      title: "Perfil actualizado",
      description: "Los cambios han sido guardados correctamente.",
    });
  };

  const handleChangePassword = async () => {
    if (passwordForm.new_password !== passwordForm.confirm_password) {
      toast({
        title: "Error",
        description: "Las contraseñas no coinciden",
        variant: "destructive",
      });
      return;
    }
    setIsSaving(true);
    await new Promise((resolve) => setTimeout(resolve, 1000));
    setIsSaving(false);
    setPasswordForm({
      current_password: "",
      new_password: "",
      confirm_password: "",
    });
    toast({
      title: "Contraseña actualizada",
      description: "Tu contraseña ha sido cambiada correctamente.",
    });
  };

  const handleSaveNotifications = async () => {
    setIsSaving(true);
    await new Promise((resolve) => setTimeout(resolve, 1000));
    setIsSaving(false);
    toast({
      title: "Notificaciones actualizadas",
      description: "Tus preferencias de notificación han sido guardadas.",
    });
  };

  const handleSaveSecurity = async () => {
    setIsSaving(true);
    await new Promise((resolve) => setTimeout(resolve, 1000));
    setIsSaving(false);
    toast({
      title: "Configuración de seguridad actualizada",
      description: "Los cambios de seguridad han sido aplicados.",
    });
  };

  const handleSaveAppearance = async () => {
    setIsSaving(true);
    await new Promise((resolve) => setTimeout(resolve, 1000));
    setIsSaving(false);
    toast({
      title: "Preferencias guardadas",
      description: "Tus preferencias de visualización han sido actualizadas.",
    });
  };

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Configuración"
        description="Administra tu cuenta y preferencias"
      />

      <Tabs defaultValue="profile" className="w-full">
        <TabsList className="bg-secondary border border-border w-full justify-start overflow-x-auto">
          <TabsTrigger value="profile" className="gap-2">
            <User className="h-4 w-4" />
            <span className="hidden sm:inline">Perfil</span>
          </TabsTrigger>
          <TabsTrigger value="security" className="gap-2">
            <Shield className="h-4 w-4" />
            <span className="hidden sm:inline">Seguridad</span>
          </TabsTrigger>
          <TabsTrigger value="notifications" className="gap-2">
            <Bell className="h-4 w-4" />
            <span className="hidden sm:inline">Notificaciones</span>
          </TabsTrigger>
          <TabsTrigger value="appearance" className="gap-2">
            <Palette className="h-4 w-4" />
            <span className="hidden sm:inline">Apariencia</span>
          </TabsTrigger>
        </TabsList>

        {/* Profile Tab */}
        <TabsContent value="profile" className="mt-6 space-y-6">
          <Card className="bg-card border-border">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <User className="h-5 w-5 text-primary" />
                Información Personal
              </CardTitle>
              <CardDescription>
                Actualiza tu información de perfil y foto
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Avatar */}
              <div className="flex items-center gap-6">
                <Avatar className="h-20 w-20">
                  <AvatarImage src={user?.avatar || "/placeholder.svg"} alt={firstName} />
                  <AvatarFallback className="bg-primary/10 text-primary text-xl">
                    {firstName?.[0]}
                    {lastName?.[0]}
                  </AvatarFallback>
                </Avatar>
                <div className="space-y-2">
                  <Button variant="outline" size="sm" className="gap-2 bg-transparent">
                    <Camera className="h-4 w-4" />
                    Cambiar Foto
                  </Button>
                  <p className="text-xs text-muted-foreground">
                    JPG, PNG o GIF. Máximo 2MB.
                  </p>
                </div>
              </div>

              <Separator />

              {/* Form */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="first_name">Nombre</Label>
                  <Input
                    id="first_name"
                    value={profileForm.first_name}
                    onChange={(e) =>
                      setProfileForm({ ...profileForm, first_name: e.target.value })
                    }
                    className="bg-secondary border-border"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="last_name">Apellido</Label>
                  <Input
                    id="last_name"
                    value={profileForm.last_name}
                    onChange={(e) =>
                      setProfileForm({ ...profileForm, last_name: e.target.value })
                    }
                    className="bg-secondary border-border"
                  />
                </div>
                <div className="space-y-2 md:col-span-2">
                  <Label htmlFor="email">Correo Electrónico</Label>
                  <Input
                    id="email"
                    type="email"
                    value={profileForm.email}
                    onChange={(e) =>
                      setProfileForm({ ...profileForm, email: e.target.value })
                    }
                    className="bg-secondary border-border"
                  />
                </div>
              </div>

              <div className="flex justify-end">
                <Button
                  onClick={handleSaveProfile}
                  disabled={isSaving}
                  className="gap-2"
                >
                  <Save className="h-4 w-4" />
                  {isSaving ? "Guardando..." : "Guardar Cambios"}
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Change Password */}
          <Card className="bg-card border-border">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Key className="h-5 w-5 text-primary" />
                Cambiar Contraseña
              </CardTitle>
              <CardDescription>
                Actualiza tu contraseña de acceso
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="current_password">Contraseña Actual</Label>
                <div className="relative">
                  <Input
                    id="current_password"
                    type={showCurrentPassword ? "text" : "password"}
                    value={passwordForm.current_password}
                    onChange={(e) =>
                      setPasswordForm({
                        ...passwordForm,
                        current_password: e.target.value,
                      })
                    }
                    className="bg-secondary border-border pr-10"
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="absolute right-0 top-0 h-full px-3 hover:bg-transparent"
                    onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                  >
                    {showCurrentPassword ? (
                      <EyeOff className="h-4 w-4 text-muted-foreground" />
                    ) : (
                      <Eye className="h-4 w-4 text-muted-foreground" />
                    )}
                  </Button>
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="new_password">Nueva Contraseña</Label>
                  <div className="relative">
                    <Input
                      id="new_password"
                      type={showNewPassword ? "text" : "password"}
                      value={passwordForm.new_password}
                      onChange={(e) =>
                        setPasswordForm({
                          ...passwordForm,
                          new_password: e.target.value,
                        })
                      }
                      className="bg-secondary border-border pr-10"
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="absolute right-0 top-0 h-full px-3 hover:bg-transparent"
                      onClick={() => setShowNewPassword(!showNewPassword)}
                    >
                      {showNewPassword ? (
                        <EyeOff className="h-4 w-4 text-muted-foreground" />
                      ) : (
                        <Eye className="h-4 w-4 text-muted-foreground" />
                      )}
                    </Button>
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="confirm_password">Confirmar Contraseña</Label>
                  <Input
                    id="confirm_password"
                    type="password"
                    value={passwordForm.confirm_password}
                    onChange={(e) =>
                      setPasswordForm({
                        ...passwordForm,
                        confirm_password: e.target.value,
                      })
                    }
                    className="bg-secondary border-border"
                  />
                </div>
              </div>
              <div className="flex justify-end">
                <Button
                  onClick={handleChangePassword}
                  disabled={isSaving || !passwordForm.current_password}
                  className="gap-2"
                >
                  <Key className="h-4 w-4" />
                  {isSaving ? "Actualizando..." : "Cambiar Contraseña"}
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Security Tab */}
        <TabsContent value="security" className="mt-6 space-y-6">
          <Card className="bg-card border-border">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Shield className="h-5 w-5 text-primary" />
                Configuración de Seguridad
              </CardTitle>
              <CardDescription>
                Configura opciones adicionales de seguridad para tu cuenta
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Two Factor */}
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>Autenticación de Dos Factores</Label>
                  <p className="text-sm text-muted-foreground">
                    Añade una capa adicional de seguridad a tu cuenta
                  </p>
                </div>
                <Switch
                  checked={security.two_factor}
                  onCheckedChange={(checked) =>
                    setSecurity({ ...security, two_factor: checked })
                  }
                />
              </div>

              <Separator />

              {/* Session Timeout */}
              <div className="space-y-2">
                <Label>Tiempo de Inactividad</Label>
                <p className="text-sm text-muted-foreground">
                  Cierra la sesión automáticamente después de un período de inactividad
                </p>
                <Select
                  value={security.session_timeout}
                  onValueChange={(value) =>
                    setSecurity({ ...security, session_timeout: value })
                  }
                >
                  <SelectTrigger className="w-[200px] bg-secondary border-border">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="15">15 minutos</SelectItem>
                    <SelectItem value="30">30 minutos</SelectItem>
                    <SelectItem value="60">1 hora</SelectItem>
                    <SelectItem value="120">2 horas</SelectItem>
                    <SelectItem value="0">Nunca</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <Separator />

              {/* IP Whitelist */}
              <div className="space-y-2">
                <Label>Lista Blanca de IPs</Label>
                <p className="text-sm text-muted-foreground">
                  Restringe el acceso solo a direcciones IP específicas (una por línea)
                </p>
                <Input
                  placeholder="192.168.1.1"
                  value={security.ip_whitelist}
                  onChange={(e) =>
                    setSecurity({ ...security, ip_whitelist: e.target.value })
                  }
                  className="bg-secondary border-border"
                />
              </div>

              <div className="flex justify-end">
                <Button
                  onClick={handleSaveSecurity}
                  disabled={isSaving}
                  className="gap-2"
                >
                  <Save className="h-4 w-4" />
                  {isSaving ? "Guardando..." : "Guardar Configuración"}
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Notifications Tab */}
        <TabsContent value="notifications" className="mt-6 space-y-6">
          <Card className="bg-card border-border">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Bell className="h-5 w-5 text-primary" />
                Preferencias de Notificación
              </CardTitle>
              <CardDescription>
                Configura cómo y cuándo deseas recibir notificaciones
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div>
                <h4 className="font-medium mb-4">Alertas de Vulnerabilidades</h4>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <Label>Vulnerabilidades Críticas</Label>
                      <p className="text-sm text-muted-foreground">
                        Recibir email cuando se detecte una vulnerabilidad crítica
                      </p>
                    </div>
                    <Switch
                      checked={notifications.email_critical}
                      onCheckedChange={(checked) =>
                        setNotifications({ ...notifications, email_critical: checked })
                      }
                    />
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <Label>Vulnerabilidades Altas</Label>
                      <p className="text-sm text-muted-foreground">
                        Recibir email cuando se detecte una vulnerabilidad alta
                      </p>
                    </div>
                    <Switch
                      checked={notifications.email_high}
                      onCheckedChange={(checked) =>
                        setNotifications({ ...notifications, email_high: checked })
                      }
                    />
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <Label>Vulnerabilidades Medias</Label>
                      <p className="text-sm text-muted-foreground">
                        Recibir email cuando se detecte una vulnerabilidad media
                      </p>
                    </div>
                    <Switch
                      checked={notifications.email_medium}
                      onCheckedChange={(checked) =>
                        setNotifications({ ...notifications, email_medium: checked })
                      }
                    />
                  </div>
                </div>
              </div>

              <Separator />

              <div>
                <h4 className="font-medium mb-4">Notificaciones de Scans</h4>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <Label>Scan Completado</Label>
                      <p className="text-sm text-muted-foreground">
                        Recibir email cuando un scan termine
                      </p>
                    </div>
                    <Switch
                      checked={notifications.email_scan_complete}
                      onCheckedChange={(checked) =>
                        setNotifications({
                          ...notifications,
                          email_scan_complete: checked,
                        })
                      }
                    />
                  </div>
                </div>
              </div>

              <Separator />

              <div>
                <h4 className="font-medium mb-4">Reportes</h4>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <Label>Resumen Diario</Label>
                      <p className="text-sm text-muted-foreground">
                        Recibir un resumen diario de actividad
                      </p>
                    </div>
                    <Switch
                      checked={notifications.daily_digest}
                      onCheckedChange={(checked) =>
                        setNotifications({ ...notifications, daily_digest: checked })
                      }
                    />
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <Label>Reporte Semanal</Label>
                      <p className="text-sm text-muted-foreground">
                        Recibir un reporte semanal completo
                      </p>
                    </div>
                    <Switch
                      checked={notifications.weekly_report}
                      onCheckedChange={(checked) =>
                        setNotifications({ ...notifications, weekly_report: checked })
                      }
                    />
                  </div>
                </div>
              </div>

              <div className="flex justify-end">
                <Button
                  onClick={handleSaveNotifications}
                  disabled={isSaving}
                  className="gap-2"
                >
                  <Save className="h-4 w-4" />
                  {isSaving ? "Guardando..." : "Guardar Preferencias"}
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Appearance Tab */}
        <TabsContent value="appearance" className="mt-6 space-y-6">
          <Card className="bg-card border-border">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Palette className="h-5 w-5 text-primary" />
                Apariencia
              </CardTitle>
              <CardDescription>
                Personaliza la apariencia de la aplicación
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <Label>Tema</Label>
                  <Select
                    value={appearance.theme}
                    onValueChange={(value) =>
                      setAppearance({ ...appearance, theme: value })
                    }
                  >
                    <SelectTrigger className="bg-secondary border-border">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="dark">Oscuro</SelectItem>
                      <SelectItem value="light">Claro</SelectItem>
                      <SelectItem value="system">Sistema</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label className="flex items-center gap-2">
                    <Globe className="h-4 w-4" />
                    Idioma
                  </Label>
                  <Select
                    value={appearance.language}
                    onValueChange={(value) =>
                      setAppearance({ ...appearance, language: value })
                    }
                  >
                    <SelectTrigger className="bg-secondary border-border">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="es">Español</SelectItem>
                      <SelectItem value="en">English</SelectItem>
                      <SelectItem value="pt">Português</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>Zona Horaria</Label>
                  <Select
                    value={appearance.timezone}
                    onValueChange={(value) =>
                      setAppearance({ ...appearance, timezone: value })
                    }
                  >
                    <SelectTrigger className="bg-secondary border-border">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="America/Mexico_City">
                        Ciudad de México (UTC-6)
                      </SelectItem>
                      <SelectItem value="America/New_York">
                        Nueva York (UTC-5)
                      </SelectItem>
                      <SelectItem value="America/Los_Angeles">
                        Los Angeles (UTC-8)
                      </SelectItem>
                      <SelectItem value="Europe/Madrid">
                        Madrid (UTC+1)
                      </SelectItem>
                      <SelectItem value="America/Bogota">
                        Bogotá (UTC-5)
                      </SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>Formato de Fecha</Label>
                  <Select
                    value={appearance.date_format}
                    onValueChange={(value) =>
                      setAppearance({ ...appearance, date_format: value })
                    }
                  >
                    <SelectTrigger className="bg-secondary border-border">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="DD/MM/YYYY">DD/MM/YYYY</SelectItem>
                      <SelectItem value="MM/DD/YYYY">MM/DD/YYYY</SelectItem>
                      <SelectItem value="YYYY-MM-DD">YYYY-MM-DD</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="flex justify-end">
                <Button
                  onClick={handleSaveAppearance}
                  disabled={isSaving}
                  className="gap-2"
                >
                  <Save className="h-4 w-4" />
                  {isSaving ? "Guardando..." : "Guardar Preferencias"}
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
