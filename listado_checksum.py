// llamada desde groovy
 def getListChecksum(repo,basePatch){
        def output =""
        //String [] listaSubfolders = ["components/sb/sb-00","components/sb/sb-01","components/vs/vs-00","components/vs/vs-01"]
        String [] listaSubfolders = ["es/es-00","sb/sb-00","sb/sb-01","vs/vs-00","vs/vs-01"]
        steps.utils.downloadAndSaveFiles(["./gitlabOps/list_checksum_Reponexus2.py"])
        steps.sh(script: """
                chmod +x ../list_checksum_Reponexus2.py
            """, returnStdout: true).trim()
  //  steps.withCredentials([steps.usernamePassword(credentialsId: 'lmm_credential', usernameVariable: 'USERNAME', passwordVariable: 'PASSWORD')]){
        def USERNAME = env.DB_USERNAME;
        def PASSWORD = env.DB_PASSWORD;
        def NEXUS_URL = env.NEXUS_URL;
        listaSubfolders.each { folder ->
            output =""
            def last_value_folder = folder.split('/')[-1].trim()
            steps.sh(script: """
                 touch listaChecksum_${last_value_folder}.json
                 truncate -s 0 listaChecksum_${last_value_folder}.json
            """, returnStdout: true).trim()
            // variable de entorno protegida
            steps.withEnv(["NEXUS_PASS=${PASSWORD}"]) {
            output = steps.sh(script: """
            python3 ../list_checksum_Reponexus2.py \
              --repo ${repo} \
              --subfolders ${folder} \
              --basePatch ${basePatch} \
              --usu ${USERNAME} \
              --urlNexus ${NEXUS_URL}/service/rest/v1/components
            """, returnStdout: true).trim()
            }
             // convertir salida en formato JSON
            def output_quoted = steps.sh(script: """
                 echo '${output}' | sed -E '1s/^\\{//; \$s/\\}//'
                 """,returnStdout: true).trim()
            // Agregar resultado al archivo
            steps.sh """
            cat <<EOF >> listaChecksum_${last_value_folder}.json
            {
               ${output_quoted}
            }
            """
            steps.sleep(time: 5, unit: 'SECONDS')
            println "Pausa finalizada."
            // Archivar el archivo como artefacto del build
            steps.archiveArtifacts artifacts: "listaChecksum_${last_value_folder}.json", fingerprint: true
        }
       // }
    }


==============================================
Python
=============
import requests
from requests.auth import HTTPBasicAuth
import argparse
import json
import sys
import os
from pathlib import Path


def get_jar_files(repository,subfolders,basePatch,usu,urlNexus):
    params = {
        "repository": repository
    }
    jar_files = []
    checksum_files = []
    continuation_token = None
    USERNAME = usu
    PASSWORD = clavepass
    NEXUS_URL = urlNexus
    
    while True:
        if continuation_token:
            params["continuationToken"] = continuation_token
        jar_md5_string = ""
        try:
            response = requests.get(
                NEXUS_URL,
                auth=HTTPBasicAuth(USERNAME, PASSWORD),
                params=params,
                verify=False,  # Cambiar a True si tienes certificado válido
                timeout=10
            )
        except requests.exceptions.RequestException as e:
            print(json.dumps({"error": f"Error de conexión: {e}"}))
            sys.exit(1)

        if response.status_code == 404:
            print(json.dumps({"error": f"Repositorio '{repository}' no encontrado (404)."}))
            sys.exit(1)
        elif response.status_code == 401:
            print(json.dumps({"error": "Credenciales inválidas (401 Unauthorized)."}))
            sys.exit(1)
        elif response.status_code != 200:
            print(json.dumps({"error": f"Error HTTP {response.status_code}: {response.text}"}))
            break

        data = response.json()

        for item in data.get("items", []):
            for asset in item.get("assets", []):
                path = asset.get("path", "")
                if basePatch in path and subfolders in path and ("appjar" in path or "staticContent" in path) and path.endswith((".jar", ".tar.gz", ".zip")):
                    jar_md5 = asset.get("checksum", {}).get("md5")
                    if jar_md5:
                       checksum_files.append(jar_md5)
        continuation_token = data.get("continuationToken")
        if not continuation_token:
            break
    return sorted(checksum_files)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="List .jar-checksum files from Nexus repository inside a base path.")
    parser.add_argument('--repo', required=True, help='Nombre del repositorio en Nexus')
    parser.add_argument('--subfolders', required=True, help='subfolder components - vs necesarios para obtener artefactos')
    parser.add_argument('--basePatch', required=True, help='Ruta base para buscar artefactos en nexus')
    parser.add_argument('--usu', required=True, help='Usuario administrador nexus')
    parser.add_argument('--urlNexus', required=True, help='URL Nexus para buscar los checksum registrados')
    args = parser.parse_args()
    clavepass = os.environ.get("NEXUS_PASS")
    if not clavepass:
        print(json.dumps({"error": "La variable de entorno NEXUS_PASS no está definida"}))
        sys.exit(1)

    checkJarsTags = get_jar_files(args.repo,args.subfolders,args.basePatch,args.usu,args.urlNexus)
    print(json.dumps({"checksum_files": checkJarsTags}, indent=2))
