/////////////////////////////////////////////////////////////////////////////
//
// worlddecor.inc - мировой декор Британии.
//
// Обстановка домов, лавок, таверн и доков на живых шардах хранится
// динамическими предметами: после конвертации карты из client/ её нет.
// Готовый список снят с официальной карты (пакет ModernDistro
// decoratefacets) и собран `tools/import_worlddecor.py` ->
// `config/worlddecor.cfg`.
//
// Двери сюда не входят (их расставляет worlddoors.inc), невидимые
// блокираторы тоже.
//
// Расстановка идемпотентна: реестр серийников хранится в глобальном
// свойстве, при старте недостающие предметы создаются заново, лишние
// (например, уничтоженные ГМом) не восстанавливаются без rebuild.
//
/////////////////////////////////////////////////////////////////////////////

use uo;
use os;
use cfgfile;

var WORLDDECOR_CFG          := "worlddecor";
var WORLDDECOR_REGISTRY     := "WorldDecor.Serials";
var WORLDDECOR_VERSION_PROP := "WorldDecor.Version";
var WORLDDECOR_DATA_VERSION := 2;
var WORLDDECOR_CPROP        := "WorldDecorStatic";


/////////////////////////////////////////////////////////////////////////////
// Загрузить реестр серийников (индекс совпадает с порядком ключей cfg).
/////////////////////////////////////////////////////////////////////////////
function WDLoadRegistry()

	var registry := GetGlobalProperty( WORLDDECOR_REGISTRY );

	if( TypeOfInt( registry ) != OT_ARRAY )
		registry := {};
	endif

	return registry;
endfunction


/////////////////////////////////////////////////////////////////////////////
// Сохранить реестр.
/////////////////////////////////////////////////////////////////////////////
function WDSaveRegistry( registry )

	SetGlobalProperty( WORLDDECOR_REGISTRY, registry );
	return registry;
endfunction


/////////////////////////////////////////////////////////////////////////////
// Пометить предмет как мировой декор.
/////////////////////////////////////////////////////////////////////////////
function WDTag( item, source )

	SetObjProperty( item, WORLDDECOR_CPROP, 1 );
	// Совместимость с инструментами decoratefacets (.udestroy).
	SetObjProperty( item, "DecorateFacetsStatic", 1 );
	if( source )
		SetObjProperty( item, "WorldDecorSource", source );
	endif
	return item;
endfunction


/////////////////////////////////////////////////////////////////////////////
// Удалить весь мировой декор, известный реестру.
//
// Возвращает struct{ Destroyed, Missing }.
/////////////////////////////////////////////////////////////////////////////
function WDRemove()

	var result := struct{ "Destroyed":=0, "Missing":=0 };

	foreach serial in WDLoadRegistry()
		if( !serial )
			continue;
		endif
		var item := SystemFindObjectBySerial( serial );
		if( item && GetObjProperty( item, WORLDDECOR_CPROP ) )
			DestroyItem( item );
			result.Destroyed += 1;
		else
			result.Missing += 1;
		endif
	endforeach

	WDSaveRegistry( {} );
	return result;
endfunction


/////////////////////////////////////////////////////////////////////////////
// Сколько предметов декора сейчас существует.
/////////////////////////////////////////////////////////////////////////////
function WDCount()

	var count := 0;

	foreach serial in WDLoadRegistry()
		if( !serial )
			continue;
		endif
		var item := SystemFindObjectBySerial( serial );
		if( item && GetObjProperty( item, WORLDDECOR_CPROP ) )
			count += 1;
		endif
	endforeach

	return count;
endfunction


/////////////////////////////////////////////////////////////////////////////
// Расставить недостающий мировой декор.
//
// Возвращает struct{ Created, Existing, Failed, Total, Message }.
/////////////////////////////////////////////////////////////////////////////
function WDPlace()

	var result := struct{ "Created":=0, "Existing":=0, "Failed":=0,
	                      "Total":=0, "Message":="" };

	var cfg := ReadConfigFile( WORLDDECOR_CFG );
	if( cfg.errortext )
		result.Message := "не удалось прочитать " + WORLDDECOR_CFG + ": " + cfg.errortext;
		return result;
	endif

	var installed := CInt( GetGlobalProperty( WORLDDECOR_VERSION_PROP ) );
	var registry := WDLoadRegistry();

	// Новый набор декора: снести старый и расставить заново.
	if( installed < WORLDDECOR_DATA_VERSION )
		if( Len( registry ) > 0 )
			var removed := WDRemove();
			Print( "WorldDecor: обновление набора, удалено старых: " + removed.Destroyed );
		endif
		registry := {};
	endif

	var keys := GetConfigIntKeys( cfg );
	var new_registry := {};
	var i := -1;

	foreach key in keys
		i += 1;
		result.Total += 1;

		var elem := FindConfigElem( cfg, key );
		var objtype := CInt( elem.Objtype );
		var x := CInt( elem.X );
		var y := CInt( elem.Y );
		var z := CInt( elem.Z );
		var amount := CInt( elem.Amount );
		var color := CInt( elem.Color );
		var realm := elem.Realm;

		if( !realm )
			realm := "britannia";
		endif
		if( !amount )
			amount := 1;
		endif

		var serial := 0;
		if( i < Len( registry ) )
			serial := registry[i];
		endif

		var item := 0;
		if( serial )
			item := SystemFindObjectBySerial( serial );
		endif

		if( item && GetObjProperty( item, WORLDDECOR_CPROP ) )
			// Декор на месте: освежаем свойства, чтобы он не распадался
			// и не был украден (например, после ручной правки мира).
			item.movable := 0;
			item.decayAt := 0;
			new_registry.append( item.serial );
			result.Existing += 1;
		else
			item := CreateItemAtLocation( x, y, z, objtype, amount, realm );
			if( item.errortext )
				result.Failed += 1;
				new_registry.append( 0 );
				if( result.Failed <= 20 )
					Print( "WorldDecor: не удалось создать " + Hex( objtype ) +
					       " в " + x + "," + y + "," + z + " (" + realm + "): " +
					       item.errortext );
				endif
			else
				item.movable := 0;
				item.decayAt := 0;
				item.color := color;
				WDTag( item, CStr( elem.Source ) );
				new_registry.append( item.serial );
				result.Created += 1;
			endif
		endif

		if( i % 100 == 0 )
			sleepms( 1 );
		endif
	endforeach

	WDSaveRegistry( new_registry );
	SetGlobalProperty( WORLDDECOR_VERSION_PROP, WORLDDECOR_DATA_VERSION );

	return result;
endfunction
