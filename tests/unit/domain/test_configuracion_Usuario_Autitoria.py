"""
Tests unitarios — Usuario, ConfiguracionAnio, Auditoria
========================================================

Ejecutar:
    pytest tests/unit/domain/test_usuario_configuracion_auditoria.py -v
"""

import json
from datetime import date, datetime, timedelta

import pytest
from pydantic import ValidationError

from src.domain.models.usuario import (
    ActualizarUsuarioDTO,
    DocenteInfoDTO,
    FiltroUsuariosDTO,
    NuevoUsuarioDTO,
    Rol,
    Usuario,
    UsuarioResumenDTO,
)
from src.domain.models.configuracion import (
    ActualizarConfiguracionAnioDTO,
    ActualizarInfoInstitucionalDTO,
    ConfiguracionAnio,
    InformacionInstitucionalDTO,
    NuevaConfiguracionAnioDTO,
)
from src.domain.models.auditoria import (
    AccionCambio,
    CrearEventoSesionDTO,
    CrearRegistroCambioDTO,
    EventoSesion,
    FiltroAuditoriaDTO,
    RegistroCambio,
    TipoEventoSesion,
)


# =============================================================================
# USUARIO
# =============================================================================

class TestUsuario:

    @pytest.fixture
    def profesor(self) -> Usuario:
        return Usuario(
            id=1,
            usuario="c.lopez",
            nombre_completo="Carlos López García",
            email="c.lopez@zeci.edu.co",
            telefono="3101234567",
            rol=Rol.PROFESOR,
        )

    def test_usuario_valido(self, profesor):
        assert profesor.esta_activo is True
        assert profesor.es_docente is True
        assert profesor.es_directivo is False

    def test_usuario_normalizado_a_minusculas(self):
        u = Usuario(usuario="C.Lopez", nombre_completo="Carlos López")
        assert u.usuario == "c.lopez"

    def test_usuario_vacio_falla(self):
        with pytest.raises(ValidationError, match="vacío"):
            Usuario(usuario="", nombre_completo="Carlos López")

    def test_usuario_con_espacios_falla(self):
        with pytest.raises(ValidationError, match="espacios"):
            Usuario(usuario="c lopez", nombre_completo="Carlos López")

    def test_usuario_muy_corto_falla(self):
        with pytest.raises(ValidationError, match="3 caracteres"):
            Usuario(usuario="ab", nombre_completo="Carlos López")

    def test_nombre_muy_corto_falla(self):
        with pytest.raises(ValidationError, match="3 caracteres"):
            Usuario(usuario="clopez", nombre_completo="AB")

    def test_email_invalido_sin_arroba_falla(self):
        with pytest.raises(ValidationError, match="'@'"):
            Usuario(usuario="clopez", nombre_completo="Carlos López",
                    email="invalido.com")

    def test_email_invalido_sin_dominio_falla(self):
        with pytest.raises(ValidationError, match="formato válido"):
            Usuario(usuario="clopez", nombre_completo="Carlos López",
                    email="c@sinpunto")

    def test_email_none_valido(self):
        u = Usuario(usuario="clopez", nombre_completo="Carlos López", email=None)
        assert u.email is None

    def test_email_vacio_devuelve_none(self):
        u = Usuario(usuario="clopez", nombre_completo="Carlos López", email="   ")
        assert u.email is None

    def test_nombre_display(self, profesor):
        assert profesor.nombre_display == "Carlos López García (c.lopez)"

    def test_puede_gestionar_evaluaciones_profesor(self, profesor):
        assert profesor.puede_gestionar_evaluaciones is True

    def test_puede_gestionar_evaluaciones_apoderado(self):
        u = Usuario(usuario="acudiente1", nombre_completo="María García",
                    rol=Rol.APODERADO)
        assert u.puede_gestionar_evaluaciones is False

    def test_desactivar(self, profesor):
        inactivo = profesor.desactivar()
        assert inactivo.activo is False
        assert profesor.activo is True   # original intacto

    def test_desactivar_ya_inactivo_falla(self, profesor):
        inactivo = profesor.desactivar()
        with pytest.raises(ValueError, match="ya está desactivado"):
            inactivo.desactivar()

    def test_reactivar(self, profesor):
        reactivado = profesor.desactivar().reactivar()
        assert reactivado.activo is True

    def test_reactivar_ya_activo_falla(self, profesor):
        with pytest.raises(ValueError, match="ya está activo"):
            profesor.reactivar()

    def test_registrar_sesion(self, profesor):
        momento = datetime(2025, 3, 15, 8, 30)
        con_sesion = profesor.registrar_sesion(momento)
        assert con_sesion.ultima_sesion == momento
        assert profesor.ultima_sesion is None   # original intacto

    def test_roles_directivos(self):
        for rol in (Rol.ADMIN, Rol.DIRECTOR, Rol.COORDINADOR):
            u = Usuario(usuario="dir1", nombre_completo="Director Test", rol=rol)
            assert u.es_directivo is True

    def test_nuevo_usuario_dto(self):
        dto = NuevoUsuarioDTO(
            usuario="p.garcia",
            nombre_completo="Pedro García",
            rol=Rol.PROFESOR,
            email="p.garcia@zeci.edu.co",
        )
        u = dto.to_usuario()
        assert isinstance(u, Usuario)
        assert u.rol == Rol.PROFESOR

    def test_nuevo_usuario_dto_usuario_corto_falla(self):
        with pytest.raises(ValidationError):
            NuevoUsuarioDTO(usuario="pg", nombre_completo="Pedro García")

    def test_actualizar_dto(self, profesor):
        dto = ActualizarUsuarioDTO(nombre_completo="Carlos A. López García")
        actualizado = dto.aplicar_a(profesor)
        assert actualizado.nombre_completo == "Carlos A. López García"
        assert actualizado.email == profesor.email

    def test_actualizar_dto_vacio_no_cambia(self, profesor):
        dto = ActualizarUsuarioDTO()
        sin_cambios = dto.aplicar_a(profesor)
        assert sin_cambios == profesor

    def test_resumen_desde_usuario(self, profesor):
        resumen = UsuarioResumenDTO.desde_usuario(profesor)
        assert resumen.nombre_completo == "Carlos López García"
        assert resumen.rol == Rol.PROFESOR

    def test_resumen_sin_id_falla(self):
        u = Usuario(usuario="sinid", nombre_completo="Sin ID")
        with pytest.raises(ValueError, match="sin id"):
            UsuarioResumenDTO.desde_usuario(u)


class TestDocenteInfoDTO:

    def test_sin_carga(self):
        info = DocenteInfoDTO(
            id=1, usuario="clopez", nombre_completo="Carlos López",
            email=None, telefono=None, activo=True,
            fecha_creacion=date.today(), ultima_sesion=None,
        )
        assert info.tiene_carga is False
        assert info.resumen_carga == "Sin carga asignada"

    def test_con_carga(self):
        info = DocenteInfoDTO(
            id=1, usuario="clopez", nombre_completo="Carlos López",
            email=None, telefono=None, activo=True,
            fecha_creacion=date.today(), ultima_sesion=None,
            total_asignaciones=3, grupos_asignados=3,
            asignaturas_asignadas=2, horas_totales=18,
        )
        assert info.tiene_carga is True
        assert "3 grupos" in info.resumen_carga
        assert "18 hrs/sem" in info.resumen_carga


# =============================================================================
# CONFIGURACION AÑO
# =============================================================================

class TestConfiguracionAnio:

    @pytest.fixture
    def config(self) -> ConfiguracionAnio:
        return ConfiguracionAnio(
            id=1,
            anio=2025,
            fecha_inicio_clases=date(2025, 1, 20),
            fecha_fin_clases=date(2025, 12, 5),
            nota_minima_aprobacion=60.0,
        )

    def test_configuracion_valida(self, config):
        assert config.activo is True
        assert config.tiene_informacion_institucional is False

    def test_anio_fuera_de_rango_falla(self):
        with pytest.raises(ValidationError, match="2000 y 2100"):
            ConfiguracionAnio(anio=1999, nota_minima_aprobacion=60.0)

    def test_nota_minima_invalida_falla(self):
        with pytest.raises(ValidationError, match="0 y 100"):
            ConfiguracionAnio(anio=2025, nota_minima_aprobacion=101.0)

    def test_fechas_invertidas_fallan(self):
        with pytest.raises(ValidationError, match="posterior"):
            ConfiguracionAnio(
                anio=2025,
                fecha_inicio_clases=date(2025, 12, 1),
                fecha_fin_clases=date(2025, 1, 1),
            )

    def test_anio_display_activo(self, config):
        assert config.anio_display == "2025 (activo)"

    def test_anio_display_inactivo(self, config):
        inactivo = config.desactivar()
        assert inactivo.anio_display == "2025"

    def test_rango_fechas_display(self, config):
        assert "2025" in config.rango_fechas_display

    def test_rango_fechas_sin_fechas(self):
        config = ConfiguracionAnio(anio=2025)
        assert config.rango_fechas_display == "Fechas no definidas"

    def test_duracion_semanas(self, config):
        dias = (date(2025, 12, 5) - date(2025, 1, 20)).days
        assert config.duracion_semanas == dias // 7

    def test_activar(self):
        inactiva = ConfiguracionAnio(anio=2024, activo=False)
        activa = inactiva.activar()
        assert activa.activo is True
        assert inactiva.activo is False   # original intacto

    def test_activar_ya_activa_falla(self, config):
        with pytest.raises(ValueError, match="ya está activo"):
            config.activar()

    def test_desactivar(self, config):
        inactiva = config.desactivar()
        assert inactiva.activo is False

    def test_desactivar_ya_inactiva_falla(self):
        inactiva = ConfiguracionAnio(anio=2024, activo=False)
        with pytest.raises(ValueError, match="ya está inactivo"):
            inactiva.desactivar()

    def test_nombre_institucion_vacio_falla(self):
        with pytest.raises(ValidationError, match="vacío"):
            ConfiguracionAnio(anio=2025, nombre_institucion="   ")

    def test_info_institucional_completa(self, config):
        con_info = config.model_copy(update={
            "dane_code": "123456789000",
            "rector": "María García Pérez",
        })
        assert con_info.tiene_informacion_institucional is True

    def test_nuevo_dto(self):
        dto = NuevaConfiguracionAnioDTO(anio=2026, nota_minima_aprobacion=60.0)
        cfg = dto.to_configuracion()
        assert isinstance(cfg, ConfiguracionAnio)
        assert cfg.anio == 2026

    def test_actualizar_nota_invalida_falla(self):
        with pytest.raises(ValidationError, match="0 y 100"):
            ActualizarConfiguracionAnioDTO(nota_minima_aprobacion=105.0)

    def test_actualizar_info_institucional(self, config):
        dto = ActualizarInfoInstitucionalDTO(
            rector="Dr. Luis Pérez",
            dane_code="123456000000",
        )
        actualizada = dto.aplicar_a(config)
        assert actualizada.rector == "Dr. Luis Pérez"
        assert actualizada.dane_code == "123456000000"
        assert actualizada.nombre_institucion == config.nombre_institucion

    def test_informacion_institucional_dto_desde_configuracion(self, config):
        config_completa = config.model_copy(update={
            "dane_code": "123456000000",
            "rector": "Dr. Luis Pérez",
        })
        info = InformacionInstitucionalDTO.desde_configuracion(config_completa)
        assert info.dane_code == "123456000000"
        assert info.anio == 2025

    def test_informacion_institucional_sin_dane_falla(self, config):
        with pytest.raises(ValueError, match="DANE"):
            InformacionInstitucionalDTO.desde_configuracion(config)

    def test_informacion_institucional_sin_rector_falla(self, config):
        sin_rector = config.model_copy(update={"dane_code": "123456000000"})
        with pytest.raises(ValueError, match="rector"):
            InformacionInstitucionalDTO.desde_configuracion(sin_rector)


# =============================================================================
# AUDITORÍA
# =============================================================================

class TestEventoSesion:

    def test_evento_login_exitoso(self):
        evt = EventoSesion(
            usuario="clopez",
            usuario_id=1,
            tipo_evento=TipoEventoSesion.LOGIN_EXITOSO,
            ip_address="192.168.1.10",
        )
        assert evt.es_exitoso is True
        assert evt.es_fallido is False

    def test_evento_login_fallido(self):
        evt = EventoSesion(
            usuario="clopez",
            tipo_evento=TipoEventoSesion.LOGIN_FALLIDO,
        )
        assert evt.es_fallido is True
        assert evt.es_exitoso is False

    def test_usuario_vacio_falla(self):
        with pytest.raises(ValidationError, match="vacío"):
            EventoSesion(usuario="   ", tipo_evento=TipoEventoSesion.LOGOUT)

    def test_detalles_vacio_es_none(self):
        evt = EventoSesion(
            usuario="clopez",
            tipo_evento=TipoEventoSesion.LOGOUT,
            detalles="   ",
        )
        assert evt.detalles is None

    def test_fecha_display(self):
        momento = datetime(2025, 3, 15, 8, 30, 0)
        evt = EventoSesion(
            usuario="clopez",
            tipo_evento=TipoEventoSesion.LOGIN_EXITOSO,
            fecha_hora=momento,
        )
        assert evt.fecha_display == "2025-03-15 08:30:00"

    def test_dto_to_evento(self):
        dto = CrearEventoSesionDTO(
            usuario="clopez",
            usuario_id=1,
            tipo_evento=TipoEventoSesion.LOGIN_EXITOSO,
        )
        evt = dto.to_evento()
        assert isinstance(evt, EventoSesion)


class TestRegistroCambio:

    def test_registro_creacion(self):
        reg = RegistroCambio.para_creacion(
            tabla="estudiantes",
            datos_nuevos={"nombre": "Ana García", "id": 1},
            registro_id=1,
            usuario_id=5,
        )
        assert reg.es_creacion is True
        assert reg.valor_anterior is None
        assert reg.nuevo_como_dict == {"nombre": "Ana García", "id": 1}

    def test_registro_actualizacion(self):
        reg = RegistroCambio.para_actualizacion(
            tabla="estudiantes",
            datos_anteriores={"nombre": "Ana García"},
            datos_nuevos={"nombre": "Ana Sofía García"},
            registro_id=1,
            usuario_id=5,
        )
        assert reg.accion == AccionCambio.UPDATE
        assert reg.anterior_como_dict == {"nombre": "Ana García"}

    def test_registro_eliminacion(self):
        reg = RegistroCambio.para_eliminacion(
            tabla="grupos",
            datos_anteriores={"codigo": "601"},
            registro_id=10,
        )
        assert reg.es_eliminacion is True
        assert reg.valor_nuevo is None

    def test_valor_dict_serializado_como_json(self):
        reg = RegistroCambio(
            accion=AccionCambio.CREATE,
            tabla="grupos",
            valor_nuevo={"codigo": "601", "grado": 6},
        )
        assert isinstance(reg.valor_nuevo, str)
        data = json.loads(reg.valor_nuevo)
        assert data["codigo"] == "601"

    def test_json_invalido_falla(self):
        with pytest.raises(ValidationError, match="JSON válido"):
            RegistroCambio(
                accion=AccionCambio.UPDATE,
                tabla="grupos",
                valor_nuevo="{invalido json",
            )

    def test_tabla_vacia_falla(self):
        with pytest.raises(ValidationError, match="vacío"):
            RegistroCambio(accion=AccionCambio.CREATE, tabla="")

    def test_dto_desde_legacy(self):
        dto = CrearRegistroCambioDTO.desde_legacy(
            tabla="usuarios",
            accion="INSERT",
            datos_nuevos={"id": 1, "usuario": "clopez"},
            descripcion="Nuevo docente",
            id_registro=1,
            usuario_id=5,
        )
        assert dto.accion == AccionCambio.CREATE
        assert dto.tabla == "usuarios"
        assert dto.registro_id == 1
        # La descripcion se agrega a datos_nuevos
        assert "_descripcion" in dto.valor_nuevo

    def test_dto_desde_legacy_accion_desconocida_usa_update(self):
        dto = CrearRegistroCambioDTO.desde_legacy(
            tabla="notas",
            accion="BULK_IMPORT",
            datos_nuevos={"count": 50},
        )
        assert dto.accion == AccionCambio.UPDATE

    def test_dto_to_registro(self):
        dto = CrearRegistroCambioDTO(
            accion=AccionCambio.DELETE,
            tabla="asignaciones",
            registro_id=7,
            usuario_id=2,
            valor_anterior={"activo": 1},
        )
        reg = dto.to_registro()
        assert isinstance(reg, RegistroCambio)
        assert reg.es_eliminacion is True


class TestFiltros:

    def test_filtro_usuarios_defecto(self):
        f = FiltroUsuariosDTO()
        assert f.solo_activos is True
        assert f.pagina == 1

    def test_filtro_auditoria_defecto(self):
        f = FiltroAuditoriaDTO()
        assert f.por_pagina == 100